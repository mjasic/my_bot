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
            # Pelna matryca (tryb 2304x1296, 16:9) -> ok. 66 st. w poziomie.
            # 640x480 z trybu 1536x864 dawalo tylko ~36 st. i tag wypadal z kadru przy dokowaniu.
            'sensor_mode': '2304:1296',
            'width': 768,
            'height': 432,
            'camera_info_url': 'file:///home/mjasic/ros2_ws/src/my_bot/config/camera_info.yaml',
            # Mniej danych w sieci: 15 klatek/s i mocniejsza kompresja JPEG
            'FrameDurationLimits': [66666, 66666],
            'jpeg_quality': 40,
            # Stala ostrosc (bez autofokusa); LensPosition w dioptriach, 1.5 = ok. 0.7 m
            # Krotka stala ekspozycja 8 ms (wzmocnienie dalej auto) - przy auto ekspozycji
            # tag rozmywal sie w obrocie 0.3 rad/s (3-6/18 detekcji zamiast 18/18)
            'ExposureTimeMode': 1,
            'ExposureTime': 8000,
            'AfMode': 0,
            'LensPosition': 1.5,
            'orientation': 180,
            # Ramka z URDF - bez tego obraz ma frame_id 'camera' i TF
            # camera_link_optical -> dock_tag nie powstaje
            'frame_id': 'camera_link_optical',
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

    # Most TF (camera_link_optical -> dock_tag) -> /detected_dock_pose dla docking_server
    dock_pose_node = Node(
        package='my_bot',
        executable='detected_dock_pose_publisher.py',
        name='detected_dock_pose_publisher',
        output='screen',
        parameters=[{
            'camera_frame': 'camera_link_optical',
            'tag_frame': 'dock_tag',
        }],
    )

    return LaunchDescription([
        camera_node,
        apriltag_node,
        dock_pose_node,
    ])
