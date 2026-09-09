import random


def play_game() -> int:
    secret_number = random.randint(1, 100)
    attempts = 0

    print("1부터 100 사이의 숫자를 맞춰보세요!")
    print("숫자를 입력하면 힌트를 드립니다.")

    while True:
        try:
            guess = int(input("숫자를 입력하세요 (1~100): "))
        except ValueError:
            print("숫자만 입력해주세요.")
            continue
        except EOFError:
            print("\n입력이 종료되어 게임을 종료합니다.")
            raise
        except KeyboardInterrupt:
            print("\n게임을 종료합니다.")
            raise

        if not 1 <= guess <= 100:
            print("1에서 100 사이의 숫자를 입력해주세요.")
            continue

        attempts += 1

        if guess < secret_number:
            print("UP! 더 큰 숫자입니다.")
        elif guess > secret_number:
            print("DOWN! 더 작은 숫자입니다.")
        else:
            print(f"정답입니다! {attempts}번 만에 맞추셨습니다.")
            return attempts


def main() -> None:
    print("=== 숫자 맞추기 게임 ===")

    while True:
        try:
            play_game()
        except (EOFError, KeyboardInterrupt):
            print("게임을 종료합니다. 안녕!")
            return

        while True:
            try:
                retry = input("다시 하시겠습니까? (y/n): ").strip().lower()
            except EOFError:
                print("\n게임을 종료합니다. 안녕!")
                return
            except KeyboardInterrupt:
                print("\n게임을 종료합니다. 안녕!")
                return

            if retry in {"y", "yes"}:
                break
            if retry in {"n", "no"}:
                print("게임을 종료합니다. 안녕!")
                return
            print("y 또는 n으로 입력해주세요.")


if __name__ == "__main__":
    main()
