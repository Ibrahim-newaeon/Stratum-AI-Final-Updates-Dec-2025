<?php

use Elementor\Widget_Base;

defined('ABSPATH') || exit;


class nextmind_widget_breadcrumb extends Widget_Base {

	public function get_name() {
		return 'nextmind-breadcrumb';
	}


	public function get_title() {
		return __( 'Nextmind - Breadcrumb', 'nextmind' );
	}


	public function get_icon() {
		return ' eicon-chevron-double-right';
	}


	public function get_categories() {
		return array( 'basic' );
	}

	public function get_keywords() {
		return array( 'awaiken', 'breadcrumbs', 'crumbs', 'list' );
	}


    protected function is_dynamic_content(): bool {
        return false;
    }
	
	protected function register_controls() {
		$this->start_controls_section(
			'breadcrumbs_section',
			[
				'label' => __( 'Settings', 'nextmind' ),
				'tab'   => \Elementor\Controls_Manager::TAB_CONTENT,
			]
		);

		$this->add_control(
			'breadcrumbs_control',
			[
				'label'   => __( 'This does nothing', 'nextmind' ),
				'type'    => \Elementor\Controls_Manager::HIDDEN,
				'default' => '',
			]
		);

		$this->end_controls_section();
	}

	protected function render() {
		do_action('nextmind_action_get_breadcrumb');
	}

}
