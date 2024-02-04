import subprocess
import time
import sys

def run_command(command):
    start = time.perf_counter()
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True)
    end = time.perf_counter()
    return (end - start, result.returncode)

def print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
    percent = "{0:.1f}".format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end="\r")
    if iteration == total:  # Print New Line on Complete
        print()

def benchmark_command(command, total_runs=50):
    times = []
    for i in range(total_runs):
        duration, returncode = run_command(command)
        if returncode != 0:
            print(f"Error executing command")
            break
        times.append(duration)
        print_progress_bar(i + 1, total_runs, prefix='Benchmarking:', suffix='Complete', length=40)
    return times

def main():
    # Default total_runs to 50 if not specified
    total_runs = 50
    if len(sys.argv) > 1:
        try:
            total_runs = int(sys.argv[1])
        except ValueError:
            print("Usage: python bench.py [total_runs]")
            sys.exit(1)

    sample_file = 'sample.bin'
    with open(sample_file, 'wb') as f:
        f.write(bytearray(10 * 1024 * 1024))  # 10MB file

    # Commands for xxd and tinyxxd
    command_base = f'xxd sample.bin sample.hex && xxd -r sample.hex sample_out.bin'
    tinyxxd_command = command_base.replace('xxd', './tinyxxd')

    print("Benchmarking xxd...")
    xxd_times = benchmark_command(command_base, total_runs)

    print("Benchmarking tinyxxd...")
    tinyxxd_times = benchmark_command(tinyxxd_command, total_runs)

    avg_xxd_time = sum(xxd_times) / len(xxd_times)
    avg_tinyxxd_time = sum(tinyxxd_times) / len(tinyxxd_times)

    if avg_xxd_time < avg_tinyxxd_time:
        print(f'On average, xxd is {((avg_tinyxxd_time - avg_xxd_time) / avg_xxd_time * 100):.2f}% faster than tinyxxd over {total_runs} runs.')
    else:
        print(f'On average, tinyxxd is {((avg_xxd_time - avg_tinyxxd_time) / avg_tinyxxd_time * 100):.2f}% faster than xxd over {total_runs} runs.')

if __name__ == '__main__':
    main()