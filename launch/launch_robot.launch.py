import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction, RegisterEventHandler, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessStart
from launch_ros.actions import Node


def generate_launch_description():
    package_name = 'my_bot'

    use_camera = LaunchConfiguration('use_camera')
    use_camera_arg = DeclareLaunchArgument(
        'use_camera',
        default_value='false',
        description='Czy uruchomic kamere i AprilTag razem z reszta robota'
    )

    use_kinect = LaunchConfiguration('use_kinect')
    use_kinect_arg = DeclareLaunchArgument(
        'use_kinect',
        default_value='false',
        description='Czy uruchomic Kinecta (RGBD) razem z reszta robota'
    )

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory(package_name), 'launch', 'rsp.launch.py'
        )]), launch_arguments={'use_sim_time': 'false', 'sim_mode': 'false'}.items()
    )
    robot_description = Command(['ros2 param get --hide-type /robot_state_publisher robot_description'])
    controller_params_file = os.path.join(get_package_share_directory(package_name), 'config', 'my_controllers.yaml')
    controller_manager = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[{'robot_description': robot_description},
                    controller_params_file,
                    {'diff_cont.enable_odom_tf': False}],
        output="screen"
    )
    delayed_controller_manager = TimerAction(period=6.0, actions=[controller_manager])
    diff_drive_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["diff_cont"],
    )
    delayed_diff_drive_spawner = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=controller_manager,
            on_start=[diff_drive_spawner],
        )
    )
    joint_broad_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_broad"],
    )
    delayed_joint_broad_spawner = RegisterEventHandler(
        event_handler=OnProcessStart(
            target_action=controller_manager,
            on_start=[joint_broad_spawner],
        )
    )

    imu_node = Node(
        package="my_bot",
        executable="mpu6500_node.py",
        name="imu_node",
        output="screen",
        remappings=[('imu/data_raw', 'imu/data')],
    )

    ekf_params_file = os.path.join(get_package_share_directory(package_name), 'config', 'ekf.yaml')
    ekf_node = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node",
        output="screen",
        parameters=[ekf_params_file],
    )
    delayed_ekf_node = TimerAction(period=20.0, actions=[ekf_node])

    twist_mux_params = os.path.join(get_package_share_directory(package_name), 'config', 'twist_mux.yaml')
    twist_mux_node = Node(
        package='twist_mux',
        executable='twist_mux',
        parameters=[twist_mux_params],
        remappings=[('/cmd_vel_out', '/diff_cont/cmd_vel')]
    )

    pi_cam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory(package_name), 'launch', 'pi_cam.launch.py'
        )]),
        condition=IfCondition(use_camera)
    )

    rplidar = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory(package_name), 'launch', 'rplidar.launch.py'
        )])
    )

    kinect = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([os.path.join(
            get_package_share_directory(package_name), 'launch', 'kinect.launch.py'
        )]),
        condition=IfCondition(use_kinect)
    )

    return LaunchDescription([
        use_camera_arg,
        use_kinect_arg,
        rsp,
        delayed_controller_manager,
        delayed_diff_drive_spawner,
        delayed_joint_broad_spawner,
        imu_node,
        delayed_ekf_node,
        twist_mux_node,
        pi_cam,
        kinect,
        rplidar,
    ])
