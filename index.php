<?php
/**
 * The site's entry point.
 *
 * Loads the relevant template part,
 * the loop is executed (when needed) by the relevant template part.
 *
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

get_header();

if ( is_page() ) {
	get_template_part( 'template-parts/page' );
} elseif ( is_singular('awaiken-portfolio') ) {
	get_template_part( 'template-parts/single-portfolio' );
} elseif ( is_singular('awaiken-project') ) {
	get_template_part( 'template-parts/single-project' );
} elseif ( is_singular('awaiken-casestudy') ) {
	get_template_part( 'template-parts/single-casestudy' );
} elseif ( is_singular() ) {
	get_template_part( 'template-parts/single' );
} elseif ( is_post_type_archive('awaiken-portfolio') || is_tax('awaiken-portfolio-category') ) {
	get_template_part( 'template-parts/archive-portfolio' );
} elseif ( is_post_type_archive('awaiken-project') || is_tax('awaiken-project-category') ) {
	get_template_part( 'template-parts/archive-project' );
} elseif ( is_post_type_archive('awaiken-casestudy') || is_tax('awaiken-casestudy-category') ) {
	get_template_part( 'template-parts/archive-casestudy' );
} elseif ( is_archive() || is_home() ) {
	get_template_part( 'template-parts/archive' );
} elseif ( is_search() ) {
	get_template_part( 'template-parts/search' );
} else {
	get_template_part( 'template-parts/404' );
}

get_footer();