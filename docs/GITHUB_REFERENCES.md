# GitHub·공식 자료의 사용 기록 (2026-11-09)

아래는 **열람·설계 참고** 기록이다. GitHub 계정 로그인, fork, clone, push, 실물 실행은 하지 않았음. 웹 공개 GitHub를 읽었다는 것과 사용자의 GitHub 저장소를 수정했다는 것은 다르다.

| 자료 | 실제 참고한 내용(어떻게) | 이번 프로젝트에서 선택한 이유 | 복제·실행 여부 |
| --- | --- | --- | --- |
| [pinklab-art/pinky_pro](https://github.com/pinklab-art/pinky_pro) | 공식 README의 Ubuntu24.04/ROS2 Jazzy 및 설치/bringup 환경 확인 | Pinky Pro ROS 2 공식 출처 | 읽기만 |
| [pinky_bringup/bringup.py](https://github.com/pinklab-art/pinky_pro/blob/main/pinky_bringup/pinky_bringup/bringup.py) | `/cmd_vel` Twist, `/odom` 경로·차동구동 개념 확인 | 기존 장비 인터페이스의 호환성 설계 | 읽기만 |
| [bringup_robot.launch.xml](https://github.com/pinklab-art/pinky_pro/blob/main/pinky_bringup/launch/bringup_robot.launch.xml) | 실제 bringup 대상 확인. 카메라 토픽 자동 실행은 가정하지 않음 | 검증 안 된 기본 카메라 토픽을 만들어 쓰지 않기 위해 | 읽기만 |
| [Pinky Pro part2](https://github.com/pinklab-art/pinky_study/wiki/2.2-Pinky-Pro(part2)) | `pinkylib.Camera()`, `start/get_frame/close`, 체커보드 보정 방식 확인 | 사용자 장비와 가까운 카메라 입력 API 참고 | 읽기만 |
| [gabrielnhn/ros2-line-follower](https://github.com/gabrielnhn/ros2-line-follower) | ROS2 Image → OpenCV → Twist 구조, 시작/정지 기능 검토 | ROS 2 인터페이스의 최소 구현 학습에 적합 | 읽기만, 코드는 복제하지 않음 |
| [follower_node.py](https://github.com/gabrielnhn/ros2-line-follower/blob/main/follower/follower/follower_node.py) | 단일 영상 중심점 + P 제어의 한계를 비교 | 검은 선 외부에서 출발하는 **정렬** 목표와 다름을 확인 | 읽기만 |
| [OpenCV Camera Calibration](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html) | intrinsic 보정과 왜곡 계수 | 픽셀 수만으로 실제 바닥 좌표를 추정하지 않기 위해 | API 활용 |
| [OpenCV Homography](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html) | 영상·바닥 대응 변환 | 거리·방향을 실제 미터/라디안 기준으로 비교 | API 활용 |

## 적용한 것

- **공식 장비 인터페이스와 카메라 API**를 우선해 자체 `camera_node.py`, `alignment_node.py`를 작성.
- 선 인식에서 기존 ROS2 라인트레이서의 **단일 중심점**보다 다중 중심점+바닥 좌표 변환+접선 추정 선택.
- 노션의 초기 권장사항에 맞춰 **회전–이동–회전**의 폐루프 정렬을 먼저 구현. Pure Pursuit는 시간 병목이 실측으로 확인된 경우에만 추후 채택 검토.
- 외부 공개 코드를 붙여넣지 않았으며, 프로그램을 GitHub에 실제 업로드하지 않았음.

## 향후 실제 기록 필요

- 사용자가 GitHub 연결을 허용한 후: 대상 저장소와 브랜치 선택, commit/PR, 링크 기록.
- 로봇 실물 사용 시: 공개 소스의 해당 commit SHA, 설치본 버전, 실제 topic/parameter dump 기록.
- 성능 시험 시: 조건별 성공률, 횡오차·방향오차, 처리 지연, CPU/RSS, 인계 결과 기록.
