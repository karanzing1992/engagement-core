<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class GREC_Repository {
	public static function table(): string {
		global $wpdb;
		return $wpdb->prefix . 'grec_comments';
	}

	public static function install(): void {
		global $wpdb;
		$table = self::table();
		$charset = $wpdb->get_charset_collate();
		require_once ABSPATH . 'wp-admin/includes/upgrade.php';
		$sql = "CREATE TABLE {$table} (
			id bigint(20) unsigned NOT NULL AUTO_INCREMENT,
			network varchar(32) NOT NULL,
			external_id varchar(191) NOT NULL,
			parent_id varchar(191) NOT NULL DEFAULT '',
			content_id varchar(191) NOT NULL DEFAULT '',
			content_title text NULL,
			author_name varchar(255) NOT NULL DEFAULT '',
			author_external_id varchar(191) NOT NULL DEFAULT '',
			author_avatar text NULL,
			comment_text longtext NULL,
			published_at datetime NULL,
			like_count int unsigned NOT NULL DEFAULT 0,
			reply_count int unsigned NOT NULL DEFAULT 0,
			moderation_status varchar(32) NOT NULL DEFAULT 'published',
			our_reply_id varchar(191) NOT NULL DEFAULT '',
			our_reply_text longtext NULL,
			replied_at datetime NULL,
			raw_json longtext NULL,
			synced_at datetime NOT NULL,
			PRIMARY KEY (id),
			UNIQUE KEY network_external (network, external_id),
			KEY content_id (content_id),
			KEY published_at (published_at),
			KEY moderation_status (moderation_status)
		) {$charset};";
		dbDelta( $sql );
	}

	public static function upsert_youtube_thread( array $thread ): void {
		global $wpdb;
		$snippet = isset( $thread['snippet'] ) && is_array( $thread['snippet'] ) ? $thread['snippet'] : array();
		$top = isset( $snippet['topLevelComment'] ) && is_array( $snippet['topLevelComment'] ) ? $snippet['topLevelComment'] : array();
		$cs = isset( $top['snippet'] ) && is_array( $top['snippet'] ) ? $top['snippet'] : array();
		$author_channel = '';
		if ( isset( $cs['authorChannelId']['value'] ) ) {
			$author_channel = sanitize_text_field( $cs['authorChannelId']['value'] );
		}
		$published = ! empty( $cs['publishedAt'] ) ? gmdate( 'Y-m-d H:i:s', strtotime( $cs['publishedAt'] ) ) : null;
		$data = array(
			'network' => 'youtube',
			'external_id' => sanitize_text_field( $top['id'] ?? '' ),
			'parent_id' => '',
			'content_id' => sanitize_text_field( $snippet['videoId'] ?? '' ),
			'content_title' => '',
			'author_name' => sanitize_text_field( $cs['authorDisplayName'] ?? '' ),
			'author_external_id' => $author_channel,
			'author_avatar' => esc_url_raw( $cs['authorProfileImageUrl'] ?? '' ),
			'comment_text' => wp_kses_post( $cs['textDisplay'] ?? $cs['textOriginal'] ?? '' ),
			'published_at' => $published,
			'like_count' => absint( $cs['likeCount'] ?? 0 ),
			'reply_count' => absint( $snippet['totalReplyCount'] ?? 0 ),
			'moderation_status' => sanitize_text_field( $cs['moderationStatus'] ?? 'published' ),
			'raw_json' => wp_json_encode( $thread ),
			'synced_at' => current_time( 'mysql', true ),
		);
		if ( '' === $data['external_id'] ) {
			return;
		}
		$existing_id = $wpdb->get_var( $wpdb->prepare( "SELECT id FROM " . self::table() . " WHERE network=%s AND external_id=%s", 'youtube', $data['external_id'] ) );
		if ( $existing_id ) {
			$wpdb->update( self::table(), $data, array( 'id' => absint( $existing_id ) ) );
		} else {
			$wpdb->insert( self::table(), $data );
		}
	}

	public static function recent( int $limit = 100 ): array {
		global $wpdb;
		$limit = max( 1, min( 250, $limit ) );
		return $wpdb->get_results( $wpdb->prepare( "SELECT * FROM " . self::table() . " ORDER BY COALESCE(published_at,synced_at) DESC LIMIT %d", $limit ), ARRAY_A );
	}

	public static function mark_replied( string $external_id, string $reply_id, string $reply_text ): void {
		global $wpdb;
		$wpdb->update(
			self::table(),
			array(
				'our_reply_id' => sanitize_text_field( $reply_id ),
				'our_reply_text' => wp_kses_post( $reply_text ),
				'replied_at' => current_time( 'mysql', true ),
			),
			array( 'network' => 'youtube', 'external_id' => sanitize_text_field( $external_id ) )
		);
	}

	public static function mark_status( string $external_id, string $status ): void {
		global $wpdb;
		$wpdb->update( self::table(), array( 'moderation_status' => sanitize_text_field( $status ) ), array( 'network' => 'youtube', 'external_id' => sanitize_text_field( $external_id ) ) );
	}
}
