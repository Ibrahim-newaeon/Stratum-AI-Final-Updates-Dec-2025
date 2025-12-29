<?php
use Elementor\Widget_Base;
use Elementor\Controls_Manager;

defined( 'ABSPATH' ) || die();

class nextmind_widget_template extends Widget_Base {

	public function __construct( $data = array(), $args = null ) {
		parent::__construct( $data, $args );
	}

	public function get_name() {
		return 'nextmind-elementor-template';
	}

	public function get_title() {
		return __( 'Nextmind - Template', 'nextmind' );
	}

	public function get_icon() {
		return 'eicon-document-file';
	}

	public function get_categories() {
		return array( 'general' );
	}
	
	public function get_keywords() {
		return [ 'nextmind', 'elementor', 'template', 'load' ];
	}

	protected function register_controls() {
		
		// Section: General ----------
		$this->start_controls_section(
			'section_general',
			[
				'label' => esc_html__( 'General', 'nextmind' ),
			]
		);
		
		$args = [
			'post_type' => 'elementor_library',
			'post_status' => 'publish',
			'meta_key' => '_elementor_template_type',
			'meta_value' => ['page', 'section', 'container'],
			'posts_per_page' => 200
		];
		
		if ( isset( $request['s'] ) ) {
			$args['s'] = $request['s'];
		}

		$options = [];
		$query = new \WP_Query( $args );

		if ( $query->have_posts() ) {
			while ( $query->have_posts() ) {
				$query->the_post();
			
				$options[get_the_ID()] = html_entity_decode(get_the_title());
			}
		}
		wp_reset_postdata();
		
		$this->add_control(
			'select_template',
			array(
				'label' => esc_html__( 'Select Template', 'nextmind' ),
				'type'        => Controls_Manager::SELECT,
				'label_block' => true,
				'multiple' => false,
				'options' => $options,
			)
		);

		$this->end_controls_section(); // End Controls Section

	}
		
	protected function render() {
		// Get Settings
		$template_id = $this->get_settings( 'select_template' );
		if ( 'publish' !== get_post_status( $template_id ) ) {
			return;
		}
		?>
		<div class="elementor-template">
			<?php
				// PHPCS - should not be escaped.
				echo \Elementor\Plugin::instance()->frontend->get_builder_content_for_display( $template_id ); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
			?>
		</div>
		<?php
		
	}
}
