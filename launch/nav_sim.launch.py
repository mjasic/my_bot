"""Nawigacja Nav2 w symulacji: mapa + AMCL + nawigacja + RViz.

Uruchom PO launch_sim.launch.py:
    ros2 launch my_bot nav_sim.launch.py
Inna mapa / bez RViz:
    ros2 launch my_bot nav_sim.launch.py map:=/sciezka/mapa.yaml rviz:=false
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('my_bot')
    nav2_share = get_package_share_directory('nav2_bringup')

    map_arg = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(pkg_share, 'maps', 'sim_map.yaml'),
        description='Mapa dla map_server/AMCL'
    )
    params_arg = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_share, 'config', 'nav2_params_sim.yaml'),
        description='Parametry Nav2'
    )
    rviz_arg = DeclareLaunchArgument(
        'rviz', default_value='true', description='Uruchom RViz'
    )

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_share, 'launch', 'bringup_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'map': LaunchConfiguration('map'),
            'params_file': LaunchConfiguration('params_file'),
        }.items()
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', os.path.join(pkg_share, 'config', 'nav.rviz')],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('rviz')),
        output='screen'
    )

    return LaunchDescription([map_arg, params_arg, rviz_arg, nav2, rviz])
