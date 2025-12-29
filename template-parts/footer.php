<?php
/**
 * The template for displaying footer.
 *
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}
?>
<footer id="site-footer" class="footer" role="contentinfo">
	<div class="footer-main">
		<div class="container">
			<div class="row align-items-center">
				<div class="col-lg-5">
					<?php	
						$footer_logo = get_theme_mod( 'footer_logo' );
						if ( !empty($footer_logo) ) {
							$image = wp_get_attachment_image_src( $footer_logo , 'full' );
							?>
							<div class="footer-logo">
								<img width="150" src="<?php echo esc_url($image[0]); ?>" alt="<?php bloginfo( 'name' ); ?>">
							</div>
							<?php 
						}
						else{
							?>
							<div class="footer-logo">
								<h4><?php echo esc_html( get_bloginfo ( 'name' ) ); ?></h4>
							</div>
							<?php 
						}
						$social_profiles = nextmind_get_social_media();
						if($social_profiles) {
						?>
						<div class="footer-social">
							<?php 
								echo wp_kses_post($social_profiles);
							?>
						</div>
						<?php 
						}
					?>
				</div>
				
				<div class="col-lg-7">
					<?php if ( has_nav_menu('footer') ) : ?>
							<?php wp_nav_menu( [ 
								'theme_location' => 'footer', 
								'container_class'=>'footer-menu', 
								'fallback_cb' => false ] 
							); 
						?>
					<?php endif; ?>
					
					<div class="copyright">
						<?php if( get_theme_mod('footer_copyright_text','') ) { ?>
							<p><?php echo wp_kses_post( get_theme_mod('footer_copyright_text') ); ?></p>
						<?php } else { ?>
							<p><?php esc_html_e( 'Created by Awaiken, Powered by WordPress. All rights reserved', 'nextmind' ); ?></p>
						<?php } ?>
					</div>
				</div>
			</div>
		</div>
	</div>
</footer>