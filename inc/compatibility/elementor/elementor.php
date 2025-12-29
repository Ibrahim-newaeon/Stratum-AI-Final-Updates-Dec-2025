<?php 

namespace Awaiken\Compatibility;

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

if( !defined( 'ELEMENTOR_VERSION' ) ) {
	return;
}

class Awaiken_Elementor { 
	private static $instance;

	public static function instance() {
		if ( is_null( self::$instance ) ) {
			self::$instance = new self();
		}
		return self::$instance;
	}
	
	public function __construct() { 
		
		add_action( 'admin_menu', [ $this, 'elementor_free_menu' ], 999 );
		add_action( 'elementor/widgets/register', [ $this, 'register_new_widgets' ] );
		
		/**
		 * Register css for elementor editor.
		 */
		add_action( 'elementor/editor/after_enqueue_styles', [ $this, 'elementor_editor_styles' ] );
		
		// enqueue modal's preview css.
		add_action( 'elementor/preview/enqueue_styles', [ $this, 'elementor_preview_styles' ] );
		
		add_action( 'init', [ $this, 'update_default_elementor_kit' ] );
		
	}
	
	public static function elementor_free_menu() {
		if ( defined( 'ELEMENTOR_PRO_VERSION' ) ) {
			return;
		}
		remove_submenu_page( 'elementor', 'e-form-submissions' );
		remove_submenu_page( 'elementor', 'elementor_custom_fonts' );
		remove_submenu_page( 'elementor', 'elementor_custom_icons' );
		remove_submenu_page( 'elementor', 'elementor_custom_code' );
		remove_submenu_page( 'elementor', 'elementor-apps' );
		remove_submenu_page( 'elementor', 'go_elementor_pro' );
	}
	
	/**
	 * Register new Elementor widgets.
	 *
	 * @param \Elementor\Widgets_Manager $widgets_manager Elementor widgets manager.
	 * @return void
	 */
	public static function register_new_widgets( $widgets_manager ) {

		require_once NEXTMIND_THEME_DIR . '/inc/compatibility/elementor/widgets/site-logo.php';
		require_once NEXTMIND_THEME_DIR . '/inc/compatibility/elementor/widgets/project.php';
		require_once NEXTMIND_THEME_DIR . '/inc/compatibility/elementor/widgets/template.php';
		require_once NEXTMIND_THEME_DIR . '/inc/compatibility/elementor/widgets/breadcrumb.php';
		require_once NEXTMIND_THEME_DIR . '/inc/compatibility/elementor/widgets/projects-slider.php';

		$widgets_manager->register( new \nextmind_widget_site_Logo() );
		$widgets_manager->register( new \nextmind_widget_project() );
		$widgets_manager->register( new \nextmind_widget_template() );
		$widgets_manager->register( new \nextmind_widget_breadcrumb() );
		$widgets_manager->register( new \nextmind_widget_projects_slider() );

	}
	
	public static function elementor_editor_styles() {
		wp_enqueue_style( 'nextmind-elementor-editor', NEXTMIND_THEME_URL . '/assets/css/elementor-editor.css', array(), NEXTMIND_THEME_VERSION );
		
		if ( !defined( 'ELEMENTOR_PRO_VERSION' ) ) {
			$custom_css = " #elementor-panel-category-pro-elements, #elementor-panel-category-theme-elements, #elementor-panel-category-theme-elements-single, #elementor-panel-category-woocommerce-elements { display: none !important; } ";
			wp_add_inline_style( 'nextmind-elementor-editor', $custom_css );
		}
	}
	
	public static function elementor_preview_styles() {
		wp_enqueue_style( 'nextmind-elementor-preview-style', NEXTMIND_THEME_URL . '/assets/css/elementor-preview.css', array(), NEXTMIND_THEME_VERSION );
	}
	
	public function update_default_elementor_kit() {

		add_option( 'default_nextmind_kit', 0 );
		if ( get_option( 'default_nextmind_kit' ) == 0 ) {

			$kit = \Elementor\Plugin::$instance->kits_manager->get_active_kit();

			if ( ! $kit->get_id() ) {
				return;
			}

			$kit->update_settings( [
				'system_colors' => array(
					 0 => array(
						'_id' => 'primary',
						'title' => 'Primary',
						'color' => '',
					 ),
					 1 => array(
						'_id' => 'secondary',
						'title' => 'Secondary',
						'color' => '',
					 ),
					 2 => array(
						'_id' => 'text',
						'title' => 'Text',
						'color' => '',
					 ),
					 3 => array(
						'_id' => 'accent',
						'title' => 'Accent',
						'color' => '',
					 ),
					 4 => array(
						'_id' => 'accentsecondary',
						'title' => 'Accent Secondary',
						'color' => '',
					 ),
					 5 => array(
						'_id' => 'white',
						'title' => 'White Color',
						'color' => '',
					 ),
					 6 => array(
						'_id' => 'black',
						'title' => 'Black Color',
						'color' => '',
					 ),
					 7 => array(
						'_id' => 'divider',
						'title' => 'Divider Color',
						'color' => '',
					 ),
					 8 => array(
						'_id' => 'darkdivider',
						'title' => 'Dark Divider Color',
						'color' => '',
					 ),
					 9 => array(
						'_id' => 'background',
						'title' => 'Background Color',
						'color' => '',
					 ),
				),
			] );

			\Elementor\Plugin::instance()->files_manager->clear_cache();
			update_option( 'default_nextmind_kit', 1 );
		}
	}
			
}
Awaiken_Elementor::instance();
