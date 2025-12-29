<?php
/**
 * Theme functions and definitions
 *
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

define( 'NEXTMIND_THEME_VERSION', wp_get_theme()->get( 'Version' ) );
define( 'NEXTMIND_THEME_DIR', get_template_directory() );
define( 'NEXTMIND_THEME_URL', get_template_directory_uri() );
define( 'AWAIKEN_ITEM_ID', 10804 );
define( 'AWAIKEN_ITEM_NAME', 'Nextmind' );
define( 'AWAIKEN_THEME_SLUG', 'nextmind' );
define( 'AWAIKEN_MP', 'TF' ); 
update_option ('nextmind_license_key','c46ec971-b24c-4db9-8765-8b9531dd5db4');
update_option ('nextmind_license_key_status','valid');
update_option ('_transient_nextmind_license_message','License key is active. Lifetime License. You have 1 / 1 sites activated.');
if ( ! isset( $content_width ) ) {
	$content_width = 800; // Pixels.
}

// Theme storage
// Attention! Must be in the global namespace to compatibility with WP-CLI
//-------------------------------------------------------------------------
$GLOBALS['NEXTMIND_STORAGE'] = array(
		'social_sharing' => 'facebook,whatsapp,linkedin',
		'social_urls' => 'https://www.instagram.com/ ,https://www.facebook.com/ ,https://www.youtube.com/',
		'show_preloader' => 0,
		'magic_cursor' => 1,
		'custom_fancy_scrollbar' => 1,
		'show_small_heading_icon' => 1,
		'small_heading_icon' => '',
		'footer_copyright_text' => '',
		'smooth_scrolling' => 0,
		'archive_page_layout' => 'full-width',
		'blog_single_page_layout' => 'full-width',
		'preloader_icon' => '',
		'project_page_title' => '',
		'project_archive_page_layout' => 'full-width',
		'project_single_page_layout' => 'full-width',
		'project_page_header_background_image' => '',
		'header_background_image' => '',
		'blog_page_header_background_image' => '',
		'not_found_image' => '',
		'not_found_heading' => '',
		'not_found_text' => '',
		'read_more_icon' => NEXTMIND_THEME_DIR.'/assets/images/arrow-dark.svg',
	    'project_btn_icon' => NEXTMIND_THEME_DIR.'/assets/images/arrow-white.svg',
		'project_btn_icon_chatbot' => NEXTMIND_THEME_DIR.'/assets/images/arrow-gradiant-nac.svg',
		'blog_btn_icon_ai_video' => NEXTMIND_THEME_DIR.'/assets/images/arrow-white-blog-ai-video.svg',
	    'blog_list_style' => '1',
		'project_list_style' => '1',
);

if ( ! function_exists( 'nextmind_slug_fonts_url' ) ) {
	function nextmind_slug_fonts_url() {
		$fonts_url = ''; 
		  
		/* Translators: If there are characters in your language that are not
		* supported by Manrope, translate this to 'off'. Do not translate
		* into your own language.
		*/
		$font = _x( 'on', 'Manrope font: on or off', 'nextmind' );
		 
		if ( 'off' !== $font ) {
			
			$font_families = array();
			 
			if ( 'off' !== $font ) {
				$font_families[] = 'Manrope:wght@200..800';
			}
			 
			$query_args = array(
				'family'	=> implode( '&family=', $font_families ),
				'display' 	=> 'swap',
			);
		
			$fonts_url = add_query_arg( $query_args, 'https://fonts.googleapis.com/css2' );
			
		}
		 
		return esc_url_raw( $fonts_url );
	}
}

if ( ! function_exists( 'nextmind_theme_setup' ) ) {
	/**
	 * Set up theme support.
	 *
	 * @return void
	 */
	function nextmind_theme_setup() {
		
		register_nav_menus( 
			array( 
					'header' => esc_html__( 'Header', 'nextmind' ) ,
					'footer' => esc_html__( 'Footer', 'nextmind' ) 
				 )		
		);

		add_theme_support( 'post-thumbnails' );
		add_theme_support( 'automatic-feed-links' );
		add_theme_support( 'title-tag' );
		add_theme_support( 'editor-styles' );
		add_theme_support(
			'html5',
			array(
				'search-form',
				'comment-form',
				'comment-list',
				'gallery',
				'caption',
				'script',
				'style',
			)
		);
		add_theme_support(
			'custom-logo',
			array(
				'height'      => 100,
				'width'       => 350,
				'flex-height' => true,
				'flex-width'  => true,
			)
		);
		
		/*
		 * Gutenberg wide images.
		 */
		add_theme_support( 'align-wide' );
		
		/**
        * Load textdomain.
        */
        load_theme_textdomain( 'nextmind', NEXTMIND_THEME_DIR . '/languages' );
		
		if ( is_admin() ) { 
			
			$nextmind_active_demo = get_option( 'nextmind_active_demo' );
			if( $nextmind_active_demo == 'ai-image' || $nextmind_active_demo == 'ai-video' || $nextmind_active_demo == 'ai-voice'  ) {
				add_editor_style( array( nextmind_slug_fonts_url(), 'assets/css/css-variable-light.css', 'assets/css/all.min.css', 'assets/css/style-editor-light.css' ) );
			}
			else{
				add_editor_style( array( nextmind_slug_fonts_url(), 'assets/css/css-variable.css', 'assets/css/all.min.css', 'style-editor.css' ) );
			}
		}
	}
}
add_action( 'after_setup_theme', 'nextmind_theme_setup' );

/**
 * Enqueue styles
 */
if ( ! function_exists( 'nextmind_theme_load_styles' ) ) {
	function nextmind_theme_load_styles() {
		
		global $NEXTMIND_STORAGE;
		$css_rules = [];
		
		if( get_option( 'nextmind_demo_imported' ) != 1 ) {
			wp_enqueue_style( 'nextmind-font', nextmind_slug_fonts_url(), array(), null );	
		}
		
		$nextmind_active_demo = get_option( 'nextmind_active_demo' );
		if( $nextmind_active_demo == 'ai-image' || $nextmind_active_demo == 'ai-video' || $nextmind_active_demo == 'ai-voice' ) {
			wp_enqueue_style( 'nextmind-css-variable', NEXTMIND_THEME_URL . '/assets/css/css-variable-light.css', array(), NEXTMIND_THEME_VERSION );
		}
		else{
			wp_enqueue_style( 'nextmind-css-variable', NEXTMIND_THEME_URL . '/assets/css/css-variable.css', array(), NEXTMIND_THEME_VERSION );
		}
		
		wp_enqueue_style( 'nextmind-css-variable', NEXTMIND_THEME_URL . '/assets/css/css-variable.css', array(), NEXTMIND_THEME_VERSION );
		wp_enqueue_style( 'fontawesome-6.4.0', NEXTMIND_THEME_URL . '/assets/css/all.min.css', array(), NEXTMIND_THEME_VERSION );
		wp_enqueue_style( 'bootstrap-5.3.2', NEXTMIND_THEME_URL . '/assets/css/bootstrap.min.css', array(), NEXTMIND_THEME_VERSION );
		wp_enqueue_style( 'nextmind-style', NEXTMIND_THEME_URL . '/style.css', array('bootstrap-5.3.2','fontawesome-6.4.0'), NEXTMIND_THEME_VERSION );
		
		$small_heading_icon =  get_theme_mod( 'small_heading_icon', $NEXTMIND_STORAGE['small_heading_icon'] );
		if( $small_heading_icon ) { 
			$background_image 	= 	wp_get_attachment_image_src( $small_heading_icon , 'full' );
			if(isset($background_image[0])) {
				$background_image	=	$background_image[0];
				$css_rules[] = ".section-title .elementor-heading-title::before,
				          		.section-title .elementor-heading-title::after,
								.ai-image .section-title .elementor-heading-title::before,
								.ai-startup .section-title .elementor-heading-title::before{
									background-image: url(" . esc_url($background_image) . ");
									mask-image: none;
									background-color: initial;
									background-size: cover;
									background-repeat: no-repeat;
								}";
			}
		}
		
		$optimized_control =  get_option( 'elementor_experiment-e_optimized_markup' );
		if($optimized_control == 'inactive') {
			$css_rules[] = ".at-shiny-glass-effect .elementor-widget-container{
				position:relative;
				overflow:hidden;
			}
			
			.at-blog-shiny-glass-effect, .at-shiny-glass-effect{
				overflow: visible;
			}

			.at-shiny-glass-effect:after{
				display: none !important;
			}

			.at-shiny-glass-effect .elementor-widget-container:after{
				content: '';
				position: absolute;
				width: 200%;
				height: 0%;
				left: 50%;
				top: 50%;
				background-color: rgba(255,255,255,.3);
				transform: translate(-50%,-50%) rotate(-45deg);
				z-index: 1;
			}

			.at-shiny-glass-effect .elementor-widget-container:hover:after{
				height: 250%;
				transition: all 600ms linear !important;
				background-color: transparent;
			}";
		}
		
		if (!empty($css_rules)) {
			wp_add_inline_style( 'nextmind-style',implode("\n", $css_rules) );
		}
		
	}
}
add_action( 'wp_enqueue_scripts', 'nextmind_theme_load_styles', 998 );

/**
 * Enqueue scripts
 */
if ( ! function_exists( 'nextmind_theme_load_scripts' ) ) {
	function nextmind_theme_load_scripts() {
		global $NEXTMIND_STORAGE;
	
		if( get_theme_mod( 'smooth_scrolling', $NEXTMIND_STORAGE['smooth_scrolling'] ) ) { 
			wp_enqueue_script( 'SmoothScroll', NEXTMIND_THEME_URL . '/assets/js/SmoothScroll.js', array( 'jquery' ), NEXTMIND_THEME_VERSION, true );
		}
		
		wp_enqueue_script( 'gsap', NEXTMIND_THEME_URL . '/assets/js/gsap.min.js', array( 'jquery' ), NEXTMIND_THEME_VERSION, true );
		if( get_theme_mod( 'magic_cursor', $NEXTMIND_STORAGE['magic_cursor'] ) ) { 
		wp_enqueue_script( 'magiccursor', NEXTMIND_THEME_URL . '/assets/js/magiccursor.js', array( 'jquery' ), NEXTMIND_THEME_VERSION, true );
		}
		
		wp_enqueue_script( 'SplitText', NEXTMIND_THEME_URL . '/assets/js/SplitText.js', array( 'jquery' ), NEXTMIND_THEME_VERSION, true );
		wp_enqueue_script( 'ScrollTrigger', NEXTMIND_THEME_URL . '/assets/js/ScrollTrigger.min.js', array( 'jquery' ), NEXTMIND_THEME_VERSION, true );
		wp_enqueue_script( 'theme-js', NEXTMIND_THEME_URL . '/assets/js/function.js', array( 'jquery' ), NEXTMIND_THEME_VERSION, true );
		
		// js for comments
		if ( is_singular() && comments_open() && get_option( 'thread_comments' ) ) {
			wp_enqueue_script( 'comment-reply' );
		}

	}
}
add_action( 'wp_enqueue_scripts', 'nextmind_theme_load_scripts' );


/**
 * Register widget area.
 */
if ( ! function_exists( 'nextmind_widgets_init' ) ) {
	function nextmind_widgets_init() {
		
		register_sidebar( array(
			'name'          => esc_html__( 'Sidebar', 'nextmind' ),
			'id'            => 'main-sidebar',
			'description'   => esc_html__( 'Add widgets here to appear in your sidebar.', 'nextmind' ),
			'before_widget' => '<aside id="%1$s" class="widget %2$s">',
			'after_widget'  => '</aside>',
			'before_title'  => '<h3 class="widget-title">',
			'after_title'   => '</h3>',
		) );
		
		register_sidebar( array(
			'name'          => esc_html__( 'Project Sidebar', 'nextmind' ),
			'id'            => 'project-sidebar',
			'description'   => esc_html__( 'Add widgets here to appear in your project sidebar.', 'nextmind' ),
			'before_widget' => '<aside id="%1$s" class="widget %2$s">',
			'after_widget'  => '</aside>',
			'before_title'  => '<h3 class="widget-title">',
			'after_title'   => '</h3>',
		) );
		
	}
}
add_action( 'widgets_init', 'nextmind_widgets_init' );


/**
*	Change post per page for Project
*/

function nextmind_pre_get_posts_project( $query ) {
	if ( ! is_admin() && $query->is_main_query() && is_post_type_archive( 'awaiken-project' ) ) {
			$query->set( 'posts_per_page', 8 );
		return;
	}
}
add_action( 'pre_get_posts', 'nextmind_pre_get_posts_project', 11 );


/**
*	Include required file
*/
require_once NEXTMIND_THEME_DIR . '/inc/init.php';