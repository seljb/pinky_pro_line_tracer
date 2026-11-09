# `config/video_observation_example.json` 사용설명서

**영상 관찰 옵션의 JSON 형식과 개발용 기본값을 보여줍니다.**

## 목차

1. [역할](#역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [완료 기준과 주의사항](#완료-기준과-주의사항)

## 역할

영상 관찰 옵션의 JSON 형식과 개발용 기본값을 보여줍니다. [원본 파일](../../../../../config/video_observation_example.json)을 확인하세요.

## 사용 순서

video_replay 명령에 --config config/video_observation_example.json을 추가합니다.

명령은 저장소 루트의 오프라인 가상환경에서 실행합니다. ROS 노드는 별도의 시스템 Jazzy 환경을 사용합니다.

## 입력과 출력

threshold·정규화 ROI·필터·표본 수를 설정합니다. method는 --methods에서 지정합니다.

## 완료 기준과 주의사항

보정 파일이 아니며 실측 최적값도 아닙니다. ROI 좌표는 0~1 픽셀 비율입니다.

[전체 파일 목차](../../../README.md)
