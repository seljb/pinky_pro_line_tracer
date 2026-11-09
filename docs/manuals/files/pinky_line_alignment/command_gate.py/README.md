# `pinky_line_alignment/command_gate.py` 사용설명서

**소프트웨어 속도 요청의 소유권·유효시간·정지 조건을 선택합니다.**

## 목차

1. [역할](#역할)
2. [사용 순서](#사용-순서)
3. [입력과 출력](#입력과-출력)
4. [완료 기준과 주의사항](#완료-기준과-주의사항)

## 역할

소프트웨어 속도 요청의 소유권·유효시간·정지 조건을 선택합니다. [원본 파일](../../../../../pinky_line_alignment/command_gate.py)을 확인하세요.

## 사용 순서

CommandGate 생성→set_enabled→select_owner→새 submit→decide 순서로 사용합니다. follower는 신선한 준비 상태도 필요합니다.

명령은 저장소 루트의 오프라인 가상환경에서 실행합니다. ROS 노드는 별도의 시스템 Jazzy 환경을 사용합니다.

## 입력과 출력

Command(m/s, rad/s) 요청을 GateDecision으로 승인 또는 0 요청으로 거부합니다.

## 완료 기준과 주의사항

기본 비활성이고 정지가 래치됩니다. 이 모듈은 실제 /cmd_vel mux·하드웨어 비상정지가 아닙니다.

[전체 파일 목차](../../../README.md)
