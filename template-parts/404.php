<?php
/**
 * The template for displaying 404 pages (not found).
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}
global $NEXTMIND_STORAGE;

$background_image 	= get_theme_mod( 'header_background_image', $NEXTMIND_STORAGE['header_background_image'] );
if($background_image) {
	$background_image 	= 	wp_get_attachment_image_src( $background_image , 'full' );
	if(isset($background_image[0])) {
		$background_image	=	$background_image[0];
	}
}

$not_found_image 	= get_theme_mod( 'not_found_image', $NEXTMIND_STORAGE['not_found_image'] );
if($not_found_image) {
	$not_found_image 	= 	wp_get_attachment_image_src( $not_found_image , 'full' );
	if(isset($not_found_image[0])) {
		$not_found_image	=	$not_found_image[0];
	}
}

?>
<main id="content" class="site-main">
	<div class="page-header" <?php if($background_image) { ?> style="background-image: url('<?php echo esc_url($background_image); ?>')" <?php } ?>>
		<div class="container">
			<div class="row align-items-center">
				<div class="col-md-12">
					<div class="page-header-box">
						<h1><?php echo esc_html__( 'Page Not Found', 'nextmind' ); ?></h1>
						<?php do_action('nextmind_action_get_breadcrumb');		?>
					</div>
				</div>
			</div>
		</div>
	</div>
	
	<div class="error-page">
		<div class="container">
			<div class="row">
				<div class="col-md-12">
					<div class="error-page-image">
						<?php if($not_found_image) { ?>
							<img src="<?php echo esc_url($not_found_image); ?>" alt="">
						<?php } else { ?>
							<img src="<?php echo NEXTMIND_THEME_URL; ?>/assets/images/404-error-img.png" alt="">
						<?php } ?>
					</div>

					<div class="error-page-content">
						<div class="error-page-content-heading">
							<?php if( get_theme_mod('not_found_heading','') ) { ?>
								<h2><?php echo wp_kses_post( get_theme_mod('not_found_heading') ); ?></h2>
							<?php } else { ?>
								<h2><?php echo esc_html__( 'Oops! page not found', 'nextmind' ); ?></h2>
							<?php } ?>
						</div>

						<div class="error-page-content-body">
							<?php if( get_theme_mod('not_found_text','') ) { ?>
								<p><?php echo wp_kses_post( get_theme_mod('not_found_text') ); ?></p>
							<?php } else { ?>
								<p><?php echo esc_html__( 'The page you are looking for does not exist.', 'nextmind' ); ?></p>
							<?php } ?>

							<?php
								printf( '<a class="btn-default" href="%s">%s</a>', esc_url( home_url() ), __('Back To Home','nextmind'));
							?>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</main>
