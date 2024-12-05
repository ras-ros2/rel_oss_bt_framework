#!/usr/bin/env python3

import os
import rclpy
from rclpy.node import Node
from pathlib import Path
from typing import List
from oss_interfaces.srv import TrajSend, SetPath, PlayPath, ActionTraj
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from rclpy.serialization import serialize_message
import json
import hashlib
from rosidl_runtime_py.set_message import set_message_fields
from builtin_interfaces.msg import Duration
from rclpy.callback_groups import ReentrantCallbackGroup
from std_srvs.srv import SetBool



class TrajectoryRecordsService(Node):
    def __init__(self):
        super().__init__("trajectory_recoder_service")
        self.get_logger().info("Node Initialized")
        self.my_callback_group = ReentrantCallbackGroup()
        self.trajectory_paths = []
        self.create_subscription(JointTrajectory, "trajectory_topic", self.save_trajectory, 10)
        self.create_service(SetPath, '/load_path', self.load_path, callback_group=self.my_callback_group)
        self.create_service(PlayPath, '/play_trajectory', self.play_trajectory, callback_group=self.my_callback_group)
        self.create_service(SetBool, '/reset_counter', self.counter_reset_callback, callback_group=self.my_callback_group)
        self.counter = 0
    
    def counter_reset_callback(self, req, resp):
        self.counter = 0
        resp.success = True
        return resp
        
    def convert_json_to_msg(self, json_obj:dict|str, msg_type: type):
        assert isinstance(msg_type, type)
        if isinstance(json_obj,str):
            json_obj = json.loads(json_obj)
        msg = msg_type()
        for field in json_obj.keys():
            assert hasattr(msg, field), f"Attribute '{field}' not found in message type {msg_type.__name__}"
        set_message_fields(msg,json_obj)
        return msg

    def save_trajectory(self, msg):
        trajectory_data = {
                "joint_names": msg.joint_names,
                "points": [{
                    "positions": list(point.positions),
                    "velocities": list(point.velocities) if point.velocities else [],
                    "accelerations": list(point.accelerations) if point.accelerations else [],
                    "effort": list(point.effort) if point.effort else [],
                    "time_from_start": {
                        "sec": point.time_from_start.sec,
                        "nanosec": point.time_from_start.nanosec
                    }
                } for point in msg.points]
            }
        self.counter += 1  # Increment the counter
        unique_id = str(self.counter)
        with open(f"/oss_sim_lab/ros2_ws/src/oss_bt_framework/xml/trajectory/{unique_id}.txt", 'w') as file:
            file.write(f"{trajectory_data}")

    def load_trajectory(self, uuid: str) -> JointTrajectory:
        path = self.trajectory_paths[len(self.trajectory_paths)-1]
        final_path = path +"/trajectory" +f"/{uuid}.txt"
        with open(final_path, 'r') as file:
            for line in file:
                traj_string = line.strip()

        
        
        json_string = traj_string.replace("'", '"')

        trajectory_data = json.loads(json_string)
        print(type(trajectory_data))
        # print(trajectory_data["size_of_json"])
        joint_trajectory = JointTrajectory()
        print(trajectory_data['joint_names'])
        joint_trajectory.joint_names = trajectory_data['joint_names']
        joint_trajectory.points = [
            JointTrajectoryPoint(
                positions=point['positions'],
                velocities=point.get('velocities', []),
                accelerations=point.get('accelerations', []),
                effort=point.get('effort', []),
                time_from_start=Duration(sec=point['time_from_start']['sec'], nanosec=point['time_from_start']['nanosec'])
            ) for point in trajectory_data['points']
        ]
        return joint_trajectory
        
    def play_trajectory(self, req, resp):
        uuid = req.unique_id
        traj = self.load_trajectory(uuid)
        topic_name = req.topic_name
        traj_client = self.create_client(ActionTraj, topic_name, callback_group=self.my_callback_group)
        request = ActionTraj.Request()
        request.traj = traj
        future = traj_client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        resp.success = True
        return resp

    def load_path(self, req, resp):
        self.trajectory_paths.append(req.path)
        return resp

def main():
    rclpy.init(args=None)
    node = TrajectoryRecordsService()
    while rclpy.ok():
        rclpy.spin_once(node)
    rclpy.shutdown()

if __name__ == "__main__":
    main()
