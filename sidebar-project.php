<?php
/**
 * The template for displaying project sidebar.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}
?>
<div class="col-lg-3 col-md-12">
	<div class="sidebar-widget">
		<?php if ( is_active_sidebar( 'project-sidebar' )  ) : ?>
			<?php dynamic_sidebar( 'project-sidebar' ); ?>
		<?php endif; ?>
	</div>
</div>