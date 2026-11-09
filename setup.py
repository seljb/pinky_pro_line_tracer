from setuptools import find_packages, setup
from glob import glob
import os

package_name = 'pinky_line_alignment'
setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['tests']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.json')),
    ],
    install_requires=['setuptools', 'numpy'],
    zip_safe=True,
    maintainer='Pinky project team',
    maintainer_email='maintainer@example.invalid',
    description='Vision-guided acquisition and alignment for Pinky Pro',
    license='Apache-2.0',
    entry_points={'console_scripts': [
        'alignment_node = pinky_line_alignment.alignment_node:main',
        'camera_node = pinky_line_alignment.camera_node:main',
        'calibrate = pinky_line_alignment.calibration:main',
        'offline_demo = pinky_line_alignment.offline_demo:main',
        'closed_loop_sim = pinky_line_alignment.closed_loop_sim:main',
    ]},
)
