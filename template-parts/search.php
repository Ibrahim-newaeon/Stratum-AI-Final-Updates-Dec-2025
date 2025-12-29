<?php
/**
 * The template for displaying search results.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}
global $NEXTMIND_STORAGE;

$blog_list_style		=	get_theme_mod( 'blog_list_style', $NEXTMIND_STORAGE['blog_list_style'] );

$archive_page_layout	=	get_theme_mod( 'archive_page_layout', 'full-width' );
if($archive_page_layout == 'full-width') {
	$column = 'col-md-12';
}
else{
	$column = 'col-lg-9 col-md-12';
}

$background_image 	= get_theme_mod( 'header_background_image', $NEXTMIND_STORAGE['header_background_image'] );
if($background_image) {
	$background_image 	= 	wp_get_attachment_image_src( $background_image , 'full' );
	if(isset($background_image[0])) {
		$background_image	=	$background_image[0];
	}
}

?>
<main id="content" class="site-main">
	<div class="page-header" <?php if($background_image) { ?> style="background-image: url('<?php echo esc_url($background_image); ?>')" <?php } ?>>
		<div class="container">
			<div class="row align-items-center">
				<div class="col-md-12">
					<div class="page-header-box">
						<h1 class="entry-title"><?php 
							$nextmind_blog_title_text = nextmind_get_archive_title();
							echo wp_kses_data( $nextmind_blog_title_text ); ?></h1>
					</div>
				</div>
			</div>
		</div>
	</div>

	<div class="page-content">
		<div class="page-blog-archive">
			<div class="container">
				<div class="row">
					<div class="<?php echo esc_attr( $column ); ?> blog-style-<?php echo esc_attr( $blog_list_style ); ?>">
						<div class="row">
							<?php if ( have_posts() ) : ?>
							<?php
								while ( have_posts() ) {
									the_post();
									$post_link = get_permalink();
									get_template_part( 'template-parts/loop/style', $blog_list_style );
							?>
						<?php } ?>
					
						<?php else : ?>
						<div class="col-md-12 text-center">
								<p><?php echo esc_html__( 'It seems we can\'t find what you\'re looking for.', 'nextmind' ); ?></p>
						</div>
					<?php endif; ?>
							<div class="col-md-12">
								<?php
									echo get_the_posts_pagination( array(
											'mid_size' => 2,
											'prev_text' => '<i class="fa-solid fa-angle-left"></i>',
											'next_text' => '<i class="fa-solid fa-angle-right"></i>',
										) );
								?>
							</div>
						</div>
					</div>
				<?php 
					if($archive_page_layout == 'with-sidebar'):
						get_sidebar();
					endif;
				?>
				</div>
			</div>
		</div>
	</div>
</main>