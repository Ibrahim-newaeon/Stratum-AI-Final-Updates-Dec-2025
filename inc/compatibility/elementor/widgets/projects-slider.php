<?php
use Elementor\Widget_Base;
use Elementor\Controls_Manager;

defined( 'ABSPATH' ) || die();

class nextmind_widget_projects_slider extends Widget_Base {

	private $_query = null;

	public function __construct( $data = array(), $args = null ) {
		parent::__construct( $data, $args );
	}

	public function get_name() {
		return 'at-projects-slider';
	}

	public function get_title() {
		return __( 'Nextmind - Projects Slider', 'nextmind' );
	}

	public function get_icon() {
		return 'eicon-post-slider';
	}

	public function get_categories() {
		return array( 'general' );
	}
	
	public function get_style_depends() {
		return ['swiper'];
	}

	public function get_query() {
		return $this->_query;
	}

	protected function _register_controls() {
		
		$this->start_controls_section(
			'section_layout',
			[
				'label' => __( 'Settings', 'nextmind' ),
				'tab' => Controls_Manager::TAB_CONTENT,
			]
		);
		
		$this->add_control(
			'posts_per_page',
			[
				'label' => esc_html__( 'Number of Projects to Display', 'nextmind' ),
				'type' => Controls_Manager::NUMBER,
				'default' => 99,
			]
		);
		
		//Category 
		$options = [];
		$taxonomies = get_terms( array(
			'taxonomy' => 'awaiken-project-category',
			'hide_empty' => true
		) );

		if (!empty($taxonomies) && !is_wp_error($taxonomies)) {
			foreach ( $taxonomies as $term ) {
				$options[$term->term_id] = html_entity_decode($term->name);
			}
		}
		
		$this->add_control(
			'projects_category',
			array(
				'label' => esc_html__( 'Projects Category', 'nextmind' ),
				'description' => esc_html__( 'Display projects from selected category.', 'nextmind' ),
				'type'        => Controls_Manager::SELECT2,
				'label_block' => true,
				'multiple' => true,
				'options' => $options,
			)
		);

		$this->add_responsive_control(
			'slider_slide_to_show',
			array(
				'label'       => esc_html__( 'Slides To Show', 'nextmind' ),
				'type'        => Controls_Manager::NUMBER,
				'min'         => 1,
				'max'         => 20,
				'step'        => 1,
				'default'     => 3,
			)
		);
		
		$this->add_responsive_control(
			'slider_slide_to_scroll',
			array(
				'label'   => esc_html__( 'Slides To Scroll', 'nextmind' ),
				'type'    => Controls_Manager::NUMBER,
				'min'     => 1,
				'max'     => 20,
				'step'    => 1,
				'default' => 1,
			)
		);

		$this->add_control(
			'slider_speed',
			array(
				'label'   => esc_html__( 'Transition duration', 'nextmind' ),
				'type'    => Controls_Manager::NUMBER,
				'min'     => 100,
				'max'     => 10000,
				'step'    => 100,
				'default' => 1000,
			)
		);

		$this->add_control(
			'slider_autoplay',
			array(
				'label'        => esc_html__( 'Autoplay', 'nextmind' ),
				'type'         => Controls_Manager::SWITCHER,
				'label_on'     => esc_html__( 'Yes', 'nextmind' ),
				'label_off'    => esc_html__( 'No', 'nextmind' ),
				'return_value' => 'yes',
				'default'      => 'yes',
			)
		);
		
		$this->add_control(
			'slider_autoplay_delay',
			array(
				'label'   => esc_html__( 'Autoplay Delay', 'nextmind' ),
				'type'    => Controls_Manager::NUMBER,
				'min'     => 100,
				'max'     => 10000,
				'step'    => 100,
				'default' => 1000,
				'condition' => array(
					'slider_autoplay' => 'yes',
				),
			)
		);
		
		$this->add_control(
			'slider_show_dot',
			array(
				'label'        => esc_html__( 'Show Dots', 'nextmind' ),
				'type'         => Controls_Manager::SWITCHER,
				'label_on'     => esc_html__( 'Yes', 'nextmind' ),
				'label_off'    => esc_html__( 'No', 'nextmind' ),
				'return_value' => 'yes',
				'default'      => '',
			)
		);

		$this->add_control(
			'slider_arrow',
			array(
				'label'        => esc_html__( 'Show Arrow', 'nextmind' ),
				'type'         => Controls_Manager::SWITCHER,
				'label_on'     => esc_html__( 'Yes', 'nextmind' ),
				'label_off'    => esc_html__( 'No', 'nextmind' ),
				'return_value' => 'yes',
				'default'      => '',
			)
		);

		$this->add_control(
			'slider_left_arrow',
			array(
				'label'     => esc_html__( 'Left Arrow Icon', 'nextmind' ),
				'type'      => Controls_Manager::ICONS,
				'default'   => array(
					'value'   => 'fas fa-angle-left',
					'library' => 'fa-solid',
				),
				'condition' => array(
					'slider_arrow' => 'yes',
				),
			)
		);

		$this->add_control(
			'slider_right_arrow',
			array(
				'label'     => esc_html__( 'Right Arrow Icon', 'nextmind' ),
				'type'      => Controls_Manager::ICONS,
				'default'   => array(
					'value'   => 'fas fa-angle-right',
					'library' => 'fa-solid',
				),
				'condition' => array(
					'slider_arrow' => 'yes',
				),
			)
		);

		$this->add_control(
			'slider_loop',
			array(
				'label'        => esc_html__( 'Loop', 'nextmind' ),
				'type'         => Controls_Manager::SWITCHER,
				'label_on'     => esc_html__( 'Yes', 'nextmind' ),
				'label_off'    => esc_html__( 'No', 'nextmind' ),
				'return_value' => 'yes',
				'default'      => '',
			)
		);

		$this->add_control(
			'slider_pause_on_hover',
			array(
				'label'        => esc_html__( 'Pause on Hover', 'nextmind' ),
				'type'         => Controls_Manager::SWITCHER,
				'label_on'     => esc_html__( 'Yes', 'nextmind' ),
				'label_off'    => esc_html__( 'No', 'nextmind' ),
				'return_value' => 'yes',
				'default'      => 'yes',
			)
		);
		
		$this->add_control(
			'centered_slides',
			array(
				'label'        => esc_html__( 'Centered Slides', 'nextmind' ),
				'type'         => Controls_Manager::SWITCHER,
				'label_on'     => esc_html__( 'Yes', 'nextmind' ),
				'label_off'    => esc_html__( 'No', 'nextmind' ),
				'return_value' => 'yes',
				'default'      => '',
			)
		);

		$this->end_controls_section();

	}
	
	public function query_posts() {
		$projects_category = $this->get_settings( 'projects_category' );
		$query_params = array(
            'post_type' => 'awaiken-project',
            'post_status' => 'publish',
			'orderby' => 'date',
			'order' => 'desc',
            'posts_per_page' => $this->get_settings( 'posts_per_page' ),
        );
		
		if(!empty($projects_category)) { 
			$query_params['tax_query']      = array(
					array(
						'taxonomy' => 'awaiken-project-category',
						'field'    => 'ID',                     
						'terms'    => $projects_category, 
					),
				);
		}
		
		$wp_query = new \WP_Query( $query_params );

		$this->_query = $wp_query;
	}

	protected function render() {

		$testimonials = array();
		$settings     = $this->get_settings_for_display();
		
		extract( $settings );

		$slides_to_show_count   = $slider_slide_to_show ? $slider_slide_to_show : 1;
		$slider_slide_to_scroll   = $slider_slide_to_scroll ? $slider_slide_to_scroll : 1;

		// Config
		$config = array(
			'rtl'            => is_rtl(),
			'arrows'         => $slider_arrow ? true : false,
			'dots'           => $slider_show_dot ? true : false,
			'pauseOnHover'   => $slider_pause_on_hover ? true : false,
			'autoplay'       => false,
			'speed'          => $slider_speed ? $slider_speed : 1000,
			'slidesPerGroup' => (int) $slider_slide_to_scroll,
			'slidesPerView'  => (int) $slides_to_show_count,
			'loop'           => ( ! empty( $slider_loop ) && $slider_loop == 'yes' ) ? true : false,
			'spaceBetween'   => 30,
			'centeredSlides'   => ( ! empty( $centered_slides ) && $centered_slides == 'yes' ) ? true : false,
			'breakpoints'    => array(
				320  => array(
					'slidesPerView'  => ! empty( $slider_slide_to_show_mobile ) ? $slider_slide_to_show_mobile : 1,
					'slidesPerGroup' => ! empty( $slider_slide_to_scroll_mobile ) ? $slider_slide_to_scroll_mobile : 1,
				),
				768  => array(
					'slidesPerView'  => ! empty( $slider_slide_to_show_tablet ) ? $slider_slide_to_show_tablet : 2,
					'slidesPerGroup' => ! empty( $slider_slide_to_scroll_tablet ) ? $slider_slide_to_scroll_tablet : 1,
				),
				1024 => array(
					'slidesPerView'  => $slides_to_show_count,
					'slidesPerGroup' => $slider_slide_to_scroll,
				),
			),
		);
		
		if( ! empty( $slider_autoplay ) && $slider_autoplay == 'yes' ) {
			$config['autoplay']  = array('delay'=>$slider_autoplay_delay);
		}

		// HTML Attribute
		$this->add_render_attribute(
			'wrapper',
			array(
				'data-config' => wp_json_encode( $config ),
			)
		);
		
		$this->query_posts();

		$wp_query = $this->get_query();

		if ( ! $wp_query->have_posts() ) {
			return;
		}
	?>
	
	<div class="at-project-slider project-slider" <?php $this->print_render_attribute_string( 'wrapper' ); ?>>
		<div class="swiper">
			<div class="swiper-wrapper">
			<?php
				global $NEXTMIND_STORAGE;
		
				while ( $wp_query->have_posts() ) {
					$wp_query->the_post();
					$projects_category = wp_get_post_terms( get_the_ID(), 'awaiken-project-category' );
				?>
				<div class="swiper-slide">
					<div class="project-slider-item bg-shape-ai-video">
						<div class="project-slider-image">
							<?php if ( has_post_thumbnail() ) : ?>
								<a href="<?php echo get_permalink(); ?>">
									<figure class="image-anime top-right-tringle-1">
										<?php the_post_thumbnail(); ?>
									</figure>
								</a>
							<?php endif; ?>
						</div>
						<div class="project-slider-content">
							<?php 
								if ($projects_category && !is_wp_error($projects_category)) {
									$first_category = $projects_category[0];
									echo '<div class="projects-slider-meta"><ul>';
									echo '<li><a href="' . esc_url(get_term_link($first_category)) . '">' . esc_html($first_category->name) . '</a></li>';
									echo '</ul></div>';
								}
							?>
							<h3><a href="<?php echo get_permalink(); ?>"><?php the_title(); ?></a></h3>
						</div>
						<div class="ai-video-readmore-btn">
							<a href="<?php echo esc_url( get_permalink() ); ?>">
								<?php echo nextmind_render_svg($NEXTMIND_STORAGE['blog_btn_icon_ai_video']); ?>
							</a>
						</div>
					</div>
				</div>
				<?php 
				}
			?>
			</div>
		<?php if ( $settings['slider_show_dot'] == 'yes' ) : ?>
			<div class="swiper-pagination"></div>
		<?php endif; ?>

		<?php if ( ! empty( $settings['slider_arrow'] ) ) : ?>
			<div class="swiper-navigation-button swiper-button-prev at-swiper-button-prev"><?php \Elementor\Icons_Manager::render_icon( $settings['slider_left_arrow'] ); ?></div>
			<div class="swiper-navigation-button swiper-button-next at-swiper-button-next"><?php \Elementor\Icons_Manager::render_icon( $settings['slider_right_arrow'] ); ?></div>
		<?php endif; ?>
		</div>
	</div>
	<?php 
		wp_reset_postdata();
	}
}