<?php 
	global $NEXTMIND_STORAGE;
	$post_link = get_permalink();
	$projects_category = wp_get_post_terms( get_the_ID(), 'awaiken-project-category' );
?>

<div class="col-md-6">
	<div class="project-item <?php if ( ! has_post_thumbnail() ) { echo 'no-image'; } ?>">
		<div class="project-item-content">
			<?php 
				if ($projects_category && !is_wp_error($projects_category)) {
					$first_category = $projects_category[0];
					echo '<div class="projects_meta"><ul>';
					echo '<li><a href="' . esc_url(get_term_link($first_category)) . '">' . esc_html($first_category->name) . '</a></li>';
					echo '</ul></div>';
				}
			?>
			<?php
				printf( '<h3><a href="%s">%s</a></h3>', esc_url( $post_link ), wp_kses_post( get_the_title()));
			?>
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