<?php 
	global $NEXTMIND_STORAGE;
	$post_link = get_permalink();
?>

<div class="col-lg-4 col-md-6">
	<div class="post-item bg-shape-ai-video <?php if ( ! has_post_thumbnail() ) { echo 'no-image'; } ?>">
		<div class="post-featured-image">
			<?php
				if ( has_post_thumbnail() ){
					printf( '<a href="%s"><figure class="at-blog-shiny-glass-effect">%s</figure></a>', esc_url( $post_link ), get_the_post_thumbnail( $post, 'large' ) );
				}
			?>                        
		</div>
		<div class="post-item-content">
			<?php
				printf( '<h2><a href="%s">%s</a></h2>', esc_url( $post_link ), wp_kses_post( get_the_title()));
			?>
		</div>
		<div class="ai-video-readmore-btn">
			<?php
				printf( '<a href="%s"> %s</a>', esc_url( $post_link ), nextmind_render_svg($NEXTMIND_STORAGE['blog_btn_icon_ai_video']));
			?>
		</div>
	</div>
</div>