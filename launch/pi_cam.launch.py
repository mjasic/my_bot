import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    camera_node = Node(
        package='camera_ros',
        executable='camera_node',
        output='screen',
        parameters=[{
            'width': 640,
            'height': 480,
            'camera_info_url': 'file:///home/mjasic/ros2_ws/src/my_bot/config/camera_info.yaml',
        }]
    )

    apriltag_params_file = os.path.join(
        get_package_share_directory('my_bot'), 'config', 'apriltag.yaml'
    )
    apriltag_node = Node(
        package='apriltag_ros',
        executable='apriltag_node',
        output='screen',
        parameters=[apriltag_params_file],
        remappings=[
            ('image_rect', '/camera/image_raw'),
            ('camera_info', '/camera/camera_info'),
        ],
    )

    return LaunchDescription([
        camera_node,
        apriltag_node,
    ])
