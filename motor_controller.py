import math

try:
    import rclpy
    from geometry_msgs.msg import Twist

    ROS_AVAILABLE = True
except ImportError:
    ROS_AVAILABLE = False


class _PrintBackend:
    """Заглушка: команды печатаются в консоль, мотор не двигается."""

    def __init__(self):
        print("Тестовый режим: ROS отключён, моторы эмулируются.")

    def drive(self, linear_x, angular_z):
        print(f"Команда: вперёд={linear_x:.2f} м/с, поворот={angular_z:.2f} рад/с")

    def stop(self):
        print("Команда: СТОП")

    def cleanup(self):
        self.stop()


class _RosBackend:
    """Публикует Twist в топик. Дальше скорость в моторы превращает ваш драйвер."""

    def __init__(self, topic):
        if not rclpy.ok():
            rclpy.init()
        self._node = rclpy.create_node("aruco_docking")
        self._pub = self._node.create_publisher(Twist, topic, 10)
        print(f"ROS 2: команды публикуются в {topic} (geometry_msgs/Twist)")

    def drive(self, linear_x, angular_z):
        msg = Twist()
        msg.linear.x = float(linear_x)
        msg.angular.z = float(angular_z)
        self._pub.publish(msg)
        rclpy.spin_once(self._node, timeout_sec=0.0)

    def stop(self):
        self.drive(0.0, 0.0)

    def cleanup(self):
        try:
            self.stop()
        finally:
            self._node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()


class MotorController:
    def __init__(self, topic="/cmd_vel", use_ros=None):
        if use_ros is None:
            use_ros = ROS_AVAILABLE
        if use_ros and not ROS_AVAILABLE:
            raise RuntimeError(
                "Запрошен ROS, но rclpy не найден. Выполните "
                "'source /opt/ros/humble/setup.bash' перед запуском."
            )
        self._backend = _RosBackend(topic) if use_ros else _PrintBackend()

    def drive(self, linear_x, angular_z):
        if not (math.isfinite(linear_x) and math.isfinite(angular_z)):
            linear_x, angular_z = 0.0, 0.0
        self._backend.drive(linear_x, angular_z)

    def stop(self):
        self._backend.stop()

    def cleanup(self):
        self._backend.cleanup()