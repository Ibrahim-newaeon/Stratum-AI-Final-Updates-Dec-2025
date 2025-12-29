<?php 
if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

function nextmind_admin_css() {
	wp_enqueue_style( 'theme-default-font-admin', nextmind_slug_fonts_url(), array(), null );
	wp_enqueue_style( 'nextmind-admin', NEXTMIND_THEME_URL . '/assets/css/admin.css', array(), NEXTMIND_THEME_VERSION );	
	
	$documentation_link = apply_filters('nextmind_documentation_link', true);

    if ($documentation_link) {
		wp_enqueue_script( 'nextmind-admin-js', NEXTMIND_THEME_URL . '/assets/js/admin.js', array( 'jquery' ), NEXTMIND_THEME_VERSION, true );    
    }
	
}

// Hook the custom_admin_css function to the admin_enqueue_scripts action.
add_action('admin_enqueue_scripts', 'nextmind_admin_css', 11);

add_action('admin_menu', 'nextmind_custom_appearance_submenu');

function nextmind_custom_appearance_submenu() {
	
    $documentation_link = apply_filters('nextmind_documentation_link', true);

    if (!$documentation_link) {
        return;
    }
	
    add_submenu_page(
        'themes.php', 
        __( 'Documentation', 'nextmind' ), 
        __( 'Documentation', 'nextmind' ), 
        'manage_options', 
        'custom_documentation_link', 
        '__return_null' 
    );
}
