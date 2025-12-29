<?php 
	global $NEXTMIND_STORAGE;
	$post_link = get_permalink();
?>

<div class="col-lg-4 col-md-6">
	<div class="post-item <?php if ( ! has_post_thumbnail() ) { echo 'no-image'; } ?>">
		<div class="post-meta">
			<p><i class="fa-solid fa-calendar-days"></i><?php echo get_the_date(); ?></p>
		</div>
		
		<div class="post-item-content">
			<?php
				printf( '<h2><a href="%s">%s</a></h2>', esc_url( $post_link ), wp_kses_post( get_the_title() ) );
			?>
			<?php the_excerpt(); ?>
		</div>
		
		<div class="post-item-btn">
			<?php
				printf( '<a href="%s">%s %s</a>', esc_url( $post_link ), __('Read More','nextmind'), nextmind_render_svg($NEXTMIND_STORAGE['read_more_icon']));
			?>
		</div>
	</div>
</div>