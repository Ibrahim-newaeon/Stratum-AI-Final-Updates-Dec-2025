<?php 
	global $NEXTMIND_STORAGE;
	$post_link = get_permalink();
?>

<div class="col-lg-4 col-md-6">
	<div class="post-item <?php if ( ! has_post_thumbnail() ) { echo 'no-image'; } ?>">
	   <div class="post-featured-image">
			<?php
				if ( has_post_thumbnail() ) {
					printf( '<a href="%s"><figure class="at-blog-shiny-glass-effect">%s</figure></a>', esc_url( $post_link ), get_the_post_thumbnail( $post, 'large' ) );
				}
			?>
		</div>
		
		<div class="post-item-body">
			<div class="post-item-content">
				<?php
					printf( '<h2><a href="%s">%s</a></h2>', esc_url( $post_link ), wp_kses_post( get_the_title()));
				?>
			</div>

			<div class="post-item-btn">
				<?php
					printf( '<a href="%s">%s %s</a>', esc_url( $post_link ), __('Read More','nextmind'), nextmind_render_svg($NEXTMIND_STORAGE['project_btn_icon']));
				?>
			</div>
		</div>
	</div>
</div>