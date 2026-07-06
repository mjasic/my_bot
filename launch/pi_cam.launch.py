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
        }]
    )

    return LaunchDescription([
        camera_node
    ])
