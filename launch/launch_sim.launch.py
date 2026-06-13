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
        launch_arguments={'use_sim_time': 'true'}.items()
    )

# =========================
# BRIDGE (ROS2 <-> GZ)
# =========================
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            # CLOCK
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock]',
            # CONTROL
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            # ODOM
            '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            # TF
            '/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V',
            # LIDAR
            '/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',
            # JOINT STATES
            '/world/empty/model/robot/joint_state@sensor_msgs/msg/JointState@gz.msgs.Model',
            # =========================
            # CAMERA (TO FIX YOUR ISSUE)
            # =========================
            '/world/empty/model/robot/link/base_link/sensor/camera/image@sensor_msgs/msg/Image@gz.msgs.Image',
            '/world/empty/model/robot/link/base_link/sensor/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo',
        ],
        remappings=[
            ('/world/empty/model/robot/joint_state', '/joint_states')
        ],
        output='screen'
    )

# =========================
# SPAWN ROBOT
# =========================
    spawn_robot = ExecuteProcess(
        cmd=[
            'bash',
            '-c',
            f'''
            xacro {pkg_share}/description/robot.urdf.xacro > /tmp/robot.urdf &&
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
        arguments=['diff_cont', '--controller-ros-args', '-r /diff_cont/cmd_vel:=/cmd_vel'],
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
        bridge,
        delayed_spawn,
        delayed_controllers
    ])