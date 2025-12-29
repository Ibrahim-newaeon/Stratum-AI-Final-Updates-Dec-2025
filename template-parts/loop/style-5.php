<?php 
	global $NEXTMIND_STORAGE;
	$post_link = get_permalink();
?>

<div class="col-lg-4 col-md-6">
	<div class="post-item <?php if ( ! has_post_thumbnail() ) { echo 'no-image'; } ?>">
		<div class="post-featured-image">
			<?php
				if ( has_post_thumbnail() ){
					printf( '<a><figure class="at-blog-shiny-glass-effect">%s</figure></a>', get_the_post_thumbnail( $post, 'large' ) );
				}
			?>                     
			<div class="ai-startup-readmore-btn">
				<?php
					printf( '<a href="%s"> %s</a>', esc_url( $post_link ), nextmind_render_svg($NEXTMIND_STORAGE['blog_btn_icon_ai_video']));
				?>
			</div>
		</div>
		<div class="post-item-body">
			<div class="post-meta">
				<p><i class="fa-solid fa-calendar-days"></i><?php echo get_the_date(); ?></p>
			</div>
			<div class="post-item-content">
				<?php
					printf( '<h2><a href="%s">%s</a></h2>', esc_url( $post_link ), wp_kses_post( get_the_title()));
				?>
			</div>
		</div>
	</div>
</div>