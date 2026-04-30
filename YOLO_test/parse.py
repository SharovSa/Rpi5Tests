import re
import pandas as pd
import sys
import argparse


def main(streams, OUTPUT):
    RUNS = 3
    pattern = re.compile(r"Latency: ([\d.]+)")

    latencies = []
    for run in range(1, RUNS + 1):
        LOG_FILE = f"./temp_log{run}.txt"
        with open(LOG_FILE, 'r') as f:
            for line in f:
                match = pattern.search(line)
                if match:
                    latencies.append(float(match.group(1)))

    df = pd.DataFrame({"latency_ms": latencies})

    result_row = pd.DataFrame([{
        "Streams": streams,
        "Avg_Latency_ms": df["latency_ms"].mean(),
        "Min_Latency_ms": df["latency_ms"].min(),
        "Max_Latency_ms": df["latency_ms"].max(),
    }])

    try:
        existing = pd.read_csv(OUTPUT)
        final_df = pd.concat([existing, result_row], ignore_index=True)
    except FileNotFoundError:
        final_df = result_row

    final_df.to_csv(OUTPUT, index=False)


def parse_args():
    parser = argparse.ArgumentParser(prog="parse")
    parser.add_argument("-s", dest="streams")
    parser.add_argument("-o", dest="output")
    args = parser.parse_args()
    return args.streams, args.output


if __name__ == '__main__':
    sys.exit(main(*parse_args()))
