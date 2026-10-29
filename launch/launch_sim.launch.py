import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess, TimerAction, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_name = 'my_bot'
    pkg_share = get_package_share_directory(package_name)

    # =========================
    # WORLD ARG
    # =========================
    world_file = LaunchConfiguration('world')
    world_arg = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_share, 'worlds', 'obstacles.world.sdf'),
        description='Gazebo world file'
    )

    # =========================
    # GAZEBO
    # =========================
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            )
        ),
        launch_arguments={
            'gz_args': ['-r ', world_file]
        }.items()
    )

    # =========================
    # ROBOT STATE PUBLISHER
    # =========================
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'rsp.launch.py')
        ),
        launch_arguments={'use_sim_time': 'true', 'sim_mode': 'true'}.items()
    )

    # =========================
    # JOYSTICK (TELEOP)
    # =========================
    joystick = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'joystick.launch.py')
        )
    )

    # =========================
    # TWIST MUX
    # =========================
    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        parameters=[
            os.path.join(pkg_share, 'config', 'twist_mux.yaml')
        ],
        remappings=[
            ('cmd_vel_out', '/diff_cont/cmd_vel')
        ],
        output='screen'
    )

    # =========================
    # BRIDGE (ROS2 <-> GZ)
    # =========================
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V',
            '/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
            '/world/empty/model/robot/joint_state@sensor_msgs/msg/JointState@gz.msgs.Model',
            '/camera/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo',
        ],
        remappings=[
            ('/world/empty/model/robot/joint_state', '/joint_states')
        ],
        output='screen'
    )

    # =========================
    # IMAGE BRIDGE (GZ -> ROS image topic)
    # =========================
    image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=['/camera/image_raw'],
        output='screen'
    )

    # =========================
    # APRILTAG NODE (sim — camera_node not needed, Gazebo publishes image+info)
    # =========================
    apriltag_node = Node(
        package='apriltag_ros',
        executable='apriltag_node',
        name='apriltag_node',
        parameters=[
            os.path.join(pkg_share, 'config', 'apriltag.yaml'),
            {'use_sim_time': True}
        ],
        remappings=[
            ('image_rect', '/camera/image_raw'),
            ('camera_info', '/camera/camera_info'),
        ],
        output='screen'
    )

    delayed_apriltag = TimerAction(
        period=8.0,
        actions=[apriltag_node]
    )

    # =========================
    # DETECTED DOCK POSE PUBLISHER
    # (bridges TF camera_link_optical -> dock_tag into detected_dock_pose
    #  topic, ktorego oczekuje SimpleChargingDock w docking_server)
    # =========================
    dock_pose_publisher = Node(
        package='my_bot',
        executable='detected_dock_pose_publisher.py',
        name='detected_dock_pose_publisher',
        parameters=[{
            'use_sim_time': True,
            'camera_frame': 'camera_link_optical',
            'tag_frame': 'dock_tag',
        }],
        output='screen'
    )

    delayed_dock_pose_publisher = TimerAction(
        period=9.0,
        actions=[dock_pose_publisher]
    )

    # =========================
    # SPAWN ROBOT
    # =========================
    spawn_robot = ExecuteProcess(
        cmd=[
            'bash',
            '-c',
            f'''
            xacro {pkg_share}/description/robot.urdf.xacro sim_mode:=true > /tmp/robot.urdf &&
            gz sdf -p /tmp/robot.urdf > /tmp/robot.sdf &&
            gz service -s /world/empty/create \
              --reqtype gz.msgs.EntityFactory \
              --reptype gz.msgs.Boolean \
              --timeout 5000 \
              --req 'sdf_filename: "/tmp/robot.sdf", name: "robot"'
            '''
        ],
        output='screen'
    )

    delayed_spawn = TimerAction(
        period=2.0,
        actions=[spawn_robot]
    )

    # =========================
    # CONTROLLER SPAWNERS
    # =========================
    diff_drive_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_cont']
    )

    joint_broad_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_broad'],
    )

    delayed_controllers = TimerAction(
        period=5.0,
        actions=[diff_drive_spawner, joint_broad_spawner]
    )

    return LaunchDescription([
        world_arg,
        gazebo,
        rsp,
        joystick,
        twist_mux,
        bridge,
        image_bridge,
        delayed_spawn,
        delayed_controllers,
        delayed_apriltag,
        delayed_dock_pose_publisher
    ])