<?php
/**
 * The template for displaying pages.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}
global $NEXTMIND_STORAGE;
while ( have_posts() ) :
	the_post();

$background_image = get_post_meta(get_the_ID(), 'awaiken_secondary_image', true);
if(empty($background_image)) {
	$background_image 	= get_theme_mod( 'header_background_image', $NEXTMIND_STORAGE['header_background_image'] );
	if($background_image) {
		$background_image 	= 	wp_get_attachment_image_src( $background_image , 'full' );
		if(isset($background_image[0])) {
			$background_image	=	$background_image[0];
		}
	}
}
?>
<main id="content" <?php post_class( 'site-main' ); ?>>
	<div class="page-header" <?php if($background_image) { ?> style="background-image: url('<?php echo esc_url($background_image); ?>')" <?php } ?>>
		<div class="container">
			<div class="row align-items-center">
				<div class="col-md-12">
					<div class="page-header-box">
						<?php the_title( '<h1 class="text-anime">', '</h1>' ); ?>
						<?php do_action('nextmind_action_get_breadcrumb');		?>
					</div>
				</div>
			</div>
		</div>
	</div>

	<div class="page-single-post single-page">
		<div class="container">
			<div class="row">
				<div class="col-md-12">
					<?php
						if ( has_post_thumbnail() ) {
							printf( '<div class="post-single-image"><a href="%s"><figure class="at-blog-shiny-glass-effect">%s</figure></a></div>', esc_url( get_permalink() ), get_the_post_thumbnail( get_the_ID(), 'large' ) );
						}
					?>
					<div class="post-content">
						<div class="post-entry nextmind-block-style">
							<?php the_content(); ?>
							<?php wp_link_pages(); ?>
						</div>
					</div>
					<?php 
						if ( comments_open() || get_comments_number() ) :
						echo '<div class="comment-box">';
							comments_template();
						echo '</div>';
						endif;
					?>
				</div>
			</div>
		</div>
	</div>
</main>
<?php
endwhile;