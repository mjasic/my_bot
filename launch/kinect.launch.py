from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    kinect_node = Node(
        package='ros2_kinect360',
        executable='ros2_kinect360_node',
        output='screen',
    )

    point_cloud_node = Node(
        package='depth_image_proc',
        executable='point_cloud_xyz_node',
        output='screen',
        remappings=[
            ('image_rect', '/depth/image_raw'),
            ('camera_info', '/depth/camera_info'),
            ('points', '/points'),
        ],
    )

    return LaunchDescription([
        kinect_node,
        point_cloud_node,
    ])
