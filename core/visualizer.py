import matplotlib.pyplot as plt
import pandas as pd


def plot_equity_curve(equity_curve: pd.Series, title: str = "Equity Curve"):
    plt.figure(figsize=(10, 4))
    plt.plot(equity_curve, label='Equity')
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show()


def plot_drawdown(equity_curve: pd.Series, title: str = "Drawdown"):
    rolling_max = equity_curve.cummax()
    drawdown = (equity_curve - rolling_max) / rolling_max

    plt.figure(figsize=(10, 3))
    plt.fill_between(drawdown.index, drawdown, color='red', alpha=0.5)
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("Drawdown")
    plt.grid(True)
    plt.tight_layout()
    plt.show()
