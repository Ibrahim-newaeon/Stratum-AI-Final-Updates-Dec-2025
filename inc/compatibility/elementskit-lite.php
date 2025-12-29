<?php
namespace Awaiken\Compatibility;

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

if ( ! class_exists( 'ElementsKit_Lite' ) ) {
	return;
}

class Awaiken_ElementsKit_Lite {

	private static $instance;

	public static function instance() {
		if ( is_null( self::$instance ) ) {
			self::$instance = new self();
		}
		return self::$instance;
	}

	public function __construct() {

		// Admin menu actions
		add_action( 'admin_menu', [ $this, 'admin_menu_actions' ], -1 );

		// Remove dashboard widgets
		add_action( 'wp_dashboard_setup', [ $this, 'remove_dashboard_widgets' ] );

		// Set onboarding status
		add_action( 'init', [ $this, 'onboarded_status' ] );

		// Dismiss banners
		add_filter( 'elementskit/license/hide_banner', '__return_true' );

		//Hide Gutenkit template library button
		add_action('admin_head', [ $this, 'admin_head_script' ]);
		
	}

	public function admin_menu_actions() {
		if ( ! current_user_can( 'manage_options' ) ) {
			return;
		}

		add_submenu_page(
			'themes.php',
			__( 'Headers', 'nextmind' ),
			__( 'Headers', 'nextmind' ),
			'manage_options',
			'edit.php?post_type=elementskit_template&elementskit_type_filter=header',
		);
		
		add_submenu_page(
			'themes.php',
			__( 'Footers', 'nextmind' ),
			__( 'Footers', 'nextmind' ),
			'manage_options',
			'edit.php?post_type=elementskit_template&elementskit_type_filter=footer',
		);
	}

	public function remove_dashboard_widgets() {
		remove_meta_box( 'wpmet-stories', 'dashboard', 'normal' );
	}

	public function onboarded_status() {

		add_option('awaiken_default_ekit_settings', 1);
		if ( get_option('awaiken_default_ekit_settings') == 1 ) {

			update_option( 'elements_kit_onboard_status', 'onboarded' );

			$elemkit_options = get_option( 'elementskit_options' );

			if ( !isset( $elemkit_options ) || !is_array( $elemkit_options ) ) {
				$elemkit_options = array();
			}

			//Modules
			$elemkit_options[ 'module_list' ][ 'elementskit-icon-pack' ][ 'status' ] = 'active';
			$elemkit_options[ 'module_list' ][ 'header-footer' ][ 'status' ] = 'active';
			$elemkit_options[ 'module_list' ][ 'megamenu' ][ 'status' ] = 'active';
			$elemkit_options[ 'module_list' ][ 'onepage-scroll' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'module_list' ][ 'widget-builder' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'module_list' ][ 'parallax' ][ 'status' ] = 'active';
			$elemkit_options[ 'module_list' ][ 'sticky-content' ][ 'status' ] = 'active';
			$elemkit_options[ 'module_list' ][ 'facebook-messenger' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'module_list' ][ 'conditional-content' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'module_list' ][ 'copy-paste-cross-domain' ][ 'status' ] = 'active';
			$elemkit_options[ 'module_list' ][ 'advanced-tooltip' ][ 'status' ] = 'active';
			$elemkit_options[ 'module_list' ][ 'pro-form-reset-button' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'module_list' ][ 'google_sheet_for_elementor_pro_form' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'module_list' ][ 'masking' ][ 'status' ] = 'active';
			$elemkit_options[ 'module_list' ][ 'particles' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'module_list' ][ 'wrapper-link' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'module_list' ][ 'glass-morphism' ][ 'status' ] = 'active';
			$elemkit_options[ 'module_list' ][ 'mouse-cursor' ][ 'status' ] = 'inactive';
			

			//Widgets General
			$elemkit_options[ 'widget_list' ][ 'image-accordion' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'accordion' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'button' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'heading' ][ 'status' ] = 'active';
			
			$elemkit_options[ 'widget_list' ][ 'icon-box' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'image-box' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'countdown-timer' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'client-logo' ][ 'status' ] = 'active';
			
			$elemkit_options[ 'widget_list' ][ 'faq' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'funfact' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'image-comparison' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'lottie' ][ 'status' ] = 'inactive';
			
			$elemkit_options[ 'widget_list' ][ 'testimonial' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'pricing' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'team' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'social' ][ 'status' ] = 'active';
			
			$elemkit_options[ 'widget_list' ][ 'progressbar' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'piechart' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'tab' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'video' ][ 'status' ] = 'active';
			
			$elemkit_options[ 'widget_list' ][ 'business-hours' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'drop-caps' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'social-share' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'dual-button' ][ 'status' ] = 'inactive';
			
			$elemkit_options[ 'widget_list' ][ 'tablepress' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'back-to-top' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'advanced-accordion' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'advanced-tab' ][ 'status' ] = 'active';
			
			$elemkit_options[ 'widget_list' ][ 'hotspot' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'motion-text' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'gallery' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'chart' ][ 'status' ] = 'inactive';
			
			$elemkit_options[ 'widget_list' ][ 'table' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'timeline' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'creative-button' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'advanced-toggle' ][ 'status' ] = 'active';
			
			$elemkit_options[ 'widget_list' ][ 'video-gallery' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'breadcrumb' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'popup-modal' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'google-map' ][ 'status' ] = 'inactive';
			
			$elemkit_options[ 'widget_list' ][ 'unfold' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'image-swap' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'whatsapp' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'advanced-slider' ][ 'status' ] = 'active';
			
			$elemkit_options[ 'widget_list' ][ 'image-hover-effect' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'fancy-animated-text' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'price-menu' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'stylish-list' ][ 'status' ] = 'inactive';
			
			$elemkit_options[ 'widget_list' ][ 'team-slider' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'audio-player' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'flip-box' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'image-morphing' ][ 'status' ] = 'inactive';
			
			$elemkit_options[ 'widget_list' ][ 'content-ticker' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'coupon-code' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'comparison-table' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'protected-content' ][ 'status' ] = 'inactive';
			
			$elemkit_options[ 'widget_list' ][ 'interactive-links' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'circle-menu' ][ 'status' ] = 'inactive';
			
			
			//Wp Posts
			$elemkit_options[ 'widget_list' ][ 'blog-posts' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'category-list' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'post-grid' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'post-list' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'post-tab' ][ 'status' ] = 'inactive';
			
			//Header Footer
			$elemkit_options[ 'widget_list' ][ 'page-list' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'nav-menu' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'header-info' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'header-search' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'header-offcanvas' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'vertical-menu' ][ 'status' ] = 'active';
			
			//Form Widgets
			$elemkit_options[ 'widget_list' ][ 'mail-chimp' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'contact-form7' ][ 'status' ] = 'active';
			$elemkit_options[ 'widget_list' ][ 'caldera-forms' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'we-forms' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'wp-forms' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'ninja-forms' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'fluent-forms' ][ 'status' ] = 'inactive';
			
			//Social Media Feeds

			$elemkit_options[ 'widget_list' ][ 'twitter-feed' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'instagram-feed' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'behance-feed' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'dribble-feed' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'facebook-feed' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'pinterest-feed' ][ 'status' ] = 'inactive';
			
			//Woocommerce
			$elemkit_options[ 'widget_list' ][ 'woo-category-list' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'woo-mini-cart' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'woo-product-carousel' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'woo-product-list' ][ 'status' ] = 'inactive';
			
			//Meeting Widgets
			$elemkit_options[ 'widget_list' ][ 'zoom' ][ 'status' ] = 'inactive';
			
			//Review Widgets
			$elemkit_options[ 'widget_list' ][ 'facebook-review' ][ 'status' ] = 'inactive';
			$elemkit_options[ 'widget_list' ][ 'yelp' ][ 'status' ] = 'inactive';

			update_option( 'elementskit_options', $elemkit_options );
			update_option('awaiken_default_ekit_settings', 0);
		}

	}
	
	public function admin_head_script() { 
	
		$license_menu 	= 	apply_filters( 'nextmind_theme_enable_elementskit_license_menu', false );
		$styles			=	array();
		if (!class_exists('Gutenkit')) {
			$styles[] = 'button.components-button.gutenkit-template-library-btn { display:none;	}';
		}
		
		if($license_menu === false) {
			$styles[] = '#adminmenu a[href^="admin.php?page=elementskit-license"] { display:none; }';
		}
		
		if($license_menu === false) {
			$styles[] = '#elementor-panel-category-pro-elements { display:none; }';
		}
		
		if( is_array($styles) && count($styles) > 0 ) {
			echo '<style>'.implode(" ",$styles).'</style>';
		}
		
	}

}
Awaiken_ElementsKit_Lite::instance();
