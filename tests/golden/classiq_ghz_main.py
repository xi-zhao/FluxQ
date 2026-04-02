from __future__ import annotations

from classiq import CX, H, Output, QArray, QBit, allocate, create_model, qfunc


@qfunc
def ghz_chain(q: QArray[QBit]) -> None:
    H(q[0])
    CX(q[0], q[1])
    CX(q[1], q[2])
    CX(q[2], q[3])


@qfunc
def main(q: Output[QArray[QBit]]) -> None:
    allocate(4, q)
    ghz_chain(q)


if __name__ == "__main__":
    qmod = create_model(main)
    print(qmod)
