<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class GREC_Gateway_Bootstrap {
	public static function init(): void {
		if ( function_exists( 'wp_register_ability' ) ) {
			add_action( 'wp_abilities_api_init', array( __CLASS__, 'register_abilities' ), 30 );
		}
	}

	public static function register_abilities(): void {
		wp_register_ability(
			'wp-control/gateway-bootstrap',
			array(
				'label'               => __( 'Bootstrap WP Control gateway', 'engagement-core' ),
				'description'         => __( 'Provision this site into a pre-registered WP Control gateway. The Cowboy backend credential is generated locally and sent directly over HTTPS; it is never returned to the caller.', 'engagement-core' ),
				'category'            => 'wp-control',
				'execute_callback'    => array( __CLASS__, 'bootstrap' ),
				'permission_callback' => static function (): bool { return current_user_can( 'manage_options' ); },
				'input_schema'        => array(
					'type'       => 'object',
					'required'   => array( 'gateway_url', 'tenant_slug' ),
					'properties' => array(
						'gateway_url' => array( 'type' => 'string' ),
						'tenant_slug' => array( 'type' => 'string' ),
					),
				),
				'meta'                => array(
					'public'       => true,
					'show_in_rest' => true,
					'annotations'  => array( 'readonly' => false, 'destructive' => false, 'idempotent' => false ),
					'mcp'          => array( 'public' => false ),
				),
			)
		);

		wp_register_ability(
			'wp-control/gateway-status',
			array(
				'label'               => __( 'WP Control gateway status', 'engagement-core' ),
				'description'         => __( 'Read the configured WP Control gateway health for this site without exposing credentials.', 'engagement-core' ),
				'category'            => 'wp-control',
				'execute_callback'    => array( __CLASS__, 'status' ),
				'permission_callback' => static function (): bool { return current_user_can( 'manage_options' ); },
				'meta'                => array(
					'public'       => true,
					'show_in_rest' => true,
					'annotations'  => array( 'readonly' => true, 'destructive' => false, 'idempotent' => true ),
					'mcp'          => array( 'public' => false ),
				),
			)
		);
	}

	public static function bootstrap( $input ) {
		if ( ! class_exists( 'Cowboy_MCP_Auth' ) ) {
			return new WP_Error( 'grec_cowboy_missing', 'Cowboy MCP is not active.' );
		}

		$input       = is_array( $input ) ? $input : array();
		$gateway_url = isset( $input['gateway_url'] ) ? esc_url_raw( $input['gateway_url'] ) : '';
		$tenant_slug = isset( $input['tenant_slug'] ) ? sanitize_key( $input['tenant_slug'] ) : '';

		if ( ! preg_match( '/^[a-z0-9][a-z0-9-]{0,62}$/', $tenant_slug ) ) {
			return new WP_Error( 'grec_invalid_tenant_slug', 'Invalid tenant slug.' );
		}
		if ( ! $gateway_url || 'https' !== wp_parse_url( $gateway_url, PHP_URL_SCHEME ) ) {
			return new WP_Error( 'grec_invalid_gateway_url', 'Gateway URL must use HTTPS.' );
		}

		$minted = Cowboy_MCP_Auth::generate_key( 'WP Control Gateway - ' . $tenant_slug, null );
		if ( empty( $minted['id'] ) || empty( $minted['key'] ) ) {
			return new WP_Error( 'grec_gateway_key_failed', 'Could not create the gateway credential.' );
		}

		$payload = array(
			'action'                => 'bootstrap',
			'tenant_slug'           => $tenant_slug,
			'site_url'              => untrailingslashit( home_url( '/' ) ),
			'mcp_endpoint'          => rest_url( 'cowboy-mcp/v1/endpoint' ),
			'backend_key'           => (string) $minted['key'],
			'backend_credential_id' => (string) $minted['id'],
		);

		$response = wp_remote_post(
			$gateway_url,
			array(
				'timeout'     => 30,
				'redirection' => 0,
				'sslverify'   => true,
				'headers'     => array( 'Content-Type' => 'application/json', 'Accept' => 'application/json' ),
				'body'        => wp_json_encode( $payload ),
			)
		);

		if ( is_wp_error( $response ) ) {
			Cowboy_MCP_Auth::revoke_key( (string) $minted['id'] );
			return $response;
		}

		$status = (int) wp_remote_retrieve_response_code( $response );
		$body   = json_decode( wp_remote_retrieve_body( $response ), true );

		if ( $status < 200 || $status >= 300 || ! is_array( $body ) || empty( $body['ok'] ) ) {
			Cowboy_MCP_Auth::revoke_key( (string) $minted['id'] );
			return new WP_Error(
				'grec_gateway_bootstrap_failed',
				is_array( $body ) && ! empty( $body['error'] ) ? sanitize_text_field( $body['error'] ) : 'Gateway bootstrap failed.',
				array( 'status' => $status )
			);
		}

		$old_id = (string) get_option( 'grec_gateway_key_id', '' );
		if ( $old_id && $old_id !== (string) $minted['id'] ) {
			Cowboy_MCP_Auth::revoke_key( $old_id );
		}

		update_option( 'grec_gateway_key_id', (string) $minted['id'], false );
		update_option( 'grec_gateway_url', $gateway_url, false );
		update_option( 'grec_gateway_tenant_slug', $tenant_slug, false );

		return array(
			'ok'              => true,
			'tenant'          => $tenant_slug,
			'gateway_url'     => $gateway_url,
			'backend_status'  => isset( $body['backend_status'] ) ? (int) $body['backend_status'] : null,
			'mcp_initialized' => ! empty( $body['mcp_initialized'] ),
			'credential_id'   => (string) $minted['id'],
			'gateway_version' => isset( $body['version'] ) ? sanitize_text_field( $body['version'] ) : '',
		);
	}

	public static function status() {
		$gateway_url = (string) get_option( 'grec_gateway_url', '' );
		$tenant_slug = (string) get_option( 'grec_gateway_tenant_slug', '' );

		if ( ! $gateway_url || ! $tenant_slug ) {
			return array( 'configured' => false );
		}

		$url = add_query_arg( 'tenant', rawurlencode( $tenant_slug ), $gateway_url );
		$r   = wp_remote_get( $url, array( 'timeout' => 12, 'sslverify' => true ) );
		if ( is_wp_error( $r ) ) {
			return new WP_Error( 'grec_gateway_health_failed', $r->get_error_message() );
		}

		return array(
			'configured' => true,
			'status'     => (int) wp_remote_retrieve_response_code( $r ),
			'gateway'    => json_decode( wp_remote_retrieve_body( $r ), true ),
		);
	}
}
