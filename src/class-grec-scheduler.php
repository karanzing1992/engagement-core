<?php
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

final class GREC_Scheduler {
	private const HOOK = 'grec_sync_youtube_comments';
	private const GROUP = 'engagement-core';

	public static function init(): void {
		add_action( self::HOOK, array( __CLASS__, 'run' ) );
		add_filter( 'cron_schedules', array( __CLASS__, 'cron_schedules' ) );
		add_action( 'action_scheduler_init', array( __CLASS__, 'ensure_scheduled' ) );
		add_action( 'init', array( __CLASS__, 'ensure_fallback_scheduled' ), 20 );
	}

	public static function cron_schedules( array $schedules ): array {
		$minutes = max( 5, absint( get_option( 'grec_sync_interval_minutes', '10' ) ) );
		$schedules['grec_custom_interval'] = array( 'interval' => $minutes * MINUTE_IN_SECONDS, 'display' => sprintf( 'Every %d minutes', $minutes ) );
		return $schedules;
	}

	public static function ensure_scheduled(): void {
		if ( function_exists( 'as_has_scheduled_action' ) && function_exists( 'as_schedule_recurring_action' ) ) {
			if ( ! as_has_scheduled_action( self::HOOK, array(), self::GROUP ) ) {
				$minutes = max( 5, absint( get_option( 'grec_sync_interval_minutes', '10' ) ) );
				as_schedule_recurring_action( time() + 60, $minutes * MINUTE_IN_SECONDS, self::HOOK, array(), self::GROUP, true );
			}
		}
	}

	public static function ensure_fallback_scheduled(): void {
		if ( function_exists( 'as_has_scheduled_action' ) && function_exists( 'as_schedule_recurring_action' ) ) {
			return;
		}
		if ( ! wp_next_scheduled( self::HOOK ) ) {
			wp_schedule_event( time() + 60, 'grec_custom_interval', self::HOOK );
		}
	}

	public static function clear(): void {
		if ( function_exists( 'as_unschedule_all_actions' ) ) {
			as_unschedule_all_actions( self::HOOK, array(), self::GROUP );
		}
		$timestamp = wp_next_scheduled( self::HOOK );
		if ( $timestamp ) {
			wp_unschedule_event( $timestamp, self::HOOK );
		}
	}

	public static function run(): void {
		if ( '1' !== get_option( 'grec_auto_sync', '1' ) ) {
			return;
		}
		$youtube = new GREC_YouTube();
		if ( ! $youtube->is_connected() ) {
			return;
		}
		try {
			$youtube->sync_recent_comments();
			delete_option( 'grec_last_error' );
		} catch ( Throwable $e ) {
			update_option( 'grec_last_error', sanitize_text_field( $e->getMessage() ), false );
		}
	}
}
