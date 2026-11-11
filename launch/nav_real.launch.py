"""Lokalizacja (AMCL + map_server) i Nav2 dla prawdziwego robota (Pi 5).

Uzycie (na Pi, po launch_robot.launch.py):
    ros2 launch my_bot nav_real.launch.py
Potem w RViz "2D Pose Estimate" w ciagu ok. 60 s - inaczej global_costmap nie wstanie.

bond_timeout 10 s: przy domyslnych 4 s menedzer lokalizacji wylaczal AMCL, gdy Pi bylo
chwilowo przeciazone (np. przy starcie Nav2) - znikalo map->odom (2026-11-11).
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import SetParameter


def generate_launch_description():
    my_bot = get_package_share_directory('my_bot')
    nav2 = get_package_share_directory('nav2_bringup')

    map_arg = DeclareLaunchArgument(
        'map', default_value=os.path.join(my_bot, 'maps', 'real_map2.yaml'))
    params_arg = DeclareLaunchArgument(
        'params_file', default_value=os.path.join(my_bot, 'config', 'nav2_params_real.yaml'))

    common = {
        'use_sim_time': 'false',
        'params_file': LaunchConfiguration('params_file'),
    }

    nav = GroupAction([
        # Dotyczy menedzerow cyklu zycia z nav2_bringup (inne wezly ignoruja ten parametr)
        SetParameter(name='bond_timeout', value=10.0),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav2, 'launch', 'localization_launch.py')),
            launch_arguments={**common, 'map': LaunchConfiguration('map')}.items()),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav2, 'launch', 'navigation_launch.py')),
            launch_arguments=common.items()),
    ])

    return LaunchDescription([map_arg, params_arg, nav])
