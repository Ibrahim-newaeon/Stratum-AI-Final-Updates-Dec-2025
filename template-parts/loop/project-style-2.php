<?php 
	global $NEXTMIND_STORAGE;
	$post_link = get_permalink();
?>

<div class="col-md-6">
	<div class="project-item <?php if ( ! has_post_thumbnail() ) { echo 'no-image'; } ?>">
		<div class="project-item-content">
			<?php
				printf( '<h3><a href="%s">%s</a></h3>', esc_url( $post_link ), wp_kses_post( get_the_title()));
			?>
			<?php the_excerpt(); ?>
		</div>
		<div class="project-image">
			<?php
				if ( has_post_thumbnail() ) {
					printf( '<a href="%s"><figure class="at-blog-shiny-glass-effect">%s</figure></a>', esc_url( $post_link ), get_the_post_thumbnail( $post, 'large' ) );
				}
			?>
		</div>
	</div>
</div>