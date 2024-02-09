#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import atexit
import os
import random
import subprocess
import time

from collections import defaultdict
from datetime import datetime
from urllib.request import urlretrieve

xxd_url = "https://raw.githubusercontent.com/vim/vim/master/src/xxd/xxd.c"
compilation_command = "gcc -std=c11 -O2 -pipe -fPIC -fno-plt -fstack-protector-strong -D_GNU_SOURCE -z norelro -Wall -Wextra -Wpedantic -Wfatal-errors"
sample_sizes = [64, 32, 10, 5, 2, 1]  # in MiB
bench_flags = ['', '-p', '-i', '-e', '-b', '-u', '-E']
results = []


def run_command(command, capture_output=False):
    """Executes a shell command, optionally capturing output, with enhanced error handling."""
    try:
        start_time = time.time()
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE if capture_output else None,
                                stderr=subprocess.PIPE if capture_output else None)
        duration = time.time() - start_time
        return duration, result.stdout if capture_output else None
    except subprocess.CalledProcessError as e:
        print_colored(f"Command failed with error: {e.stderr.decode()}", 91)  # Red text for errors
        exit(1)


def download_file(url, filename):
    """Downloads a file if it does not exist."""
    if not os.path.exists(filename):
        urlretrieve(url, filename)


def compile_programs():
    """Compiles main.c and xxd.c."""
    if not os.path.exists("og_xxd.c"):
        download_file(xxd_url, "og_xxd.c")
    compile_xxd1_cmd = compilation_command + " -o og_xxd og_xxd.c"
    run_command(compile_xxd1_cmd)
    compile_xxd2_cmd = compilation_command + " -o tinyxxd main.c"
    run_command(compile_xxd2_cmd)


def create_sample_files():
    """Creates sample files of various sizes."""
    for size in sample_sizes:
        with open(f"{size}mb.bin", "wb") as f:
            f.write(os.urandom(size * 1024 * 1024))


def benchmark_conversion(program, flags, input_file, output_file, current, total):
    """Measures the conversion time of a program, capturing output directly, and updates the progress bar with command info."""
    cmd = f"./{program} {flags} {input_file} > {output_file}"
    command_message = f"{program} {flags} on {input_file}"
    # Update progress bar with command being run
    progress_bar(current, total, message=command_message)
    start_time = time.time()
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    duration = time.time() - start_time
    if result.returncode != 0:
        print_colored("Command failed", 91)
        exit(1)
    return duration


def verify_files(file1, file2, chunk_size=1024*1024):
    """Compares two files using binary comparison in chunks to reduce memory usage."""
    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        while True:
            chunk1 = f1.read(chunk_size)
            chunk2 = f2.read(chunk_size)
            if chunk1 != chunk2:
                return False
            if not chunk1:  # End of file
                return True


def progress_bar(current, total, message="", length=50):
    """Prints a simple progress bar with percentage completion and an additional message."""
    fraction = current / total
    percent = int(fraction * 100)
    percent = min(percent, 100)
    arrow = int(fraction * length) * "="
    padding = (length - len(arrow)) * " "
    # Use blue (34) for message, green (32) for progress bar
    print(
        f"\033[2K\033[90mBenchmarking \033[37m{message}\033[0m \033[96m[{arrow}{padding}] \033[93m{percent}% \033[37m({current}/{total})\033[0m", end="\r")


def print_colored(message, color_code):
    """Prints a message in a specified ANSI color."""
    print(f"\033[{color_code}m{message}\033[0m")


def print_formatted_columns(row):
    """Prints a single row of data in columns, dynamically adjusting the width."""
    widths = [10, 10, 20, 10]  # Adjust column widths as needed
    formatted_row = " ".join(f"{str(item):<{width}}" for item, width in zip(row, widths))
    print(formatted_row)


def perform_benchmarks():
    create_sample_files()
    programs = ['og_xxd', 'tinyxxd']
    total_benchmarks = len(sample_sizes) * len(programs) * (len(bench_flags)+1)
    current_benchmark = 0

    random.seed()

    for size in sample_sizes:
        random.shuffle(programs)
        for program in programs:
            input_file = f'{size}mb.bin'
            output_file = f"{size}mb_{program}.hex"
            recon_file = f'{size}mb_recreated.bin'
            # Conversion from binary to hex
            current_benchmark += 1
            conversion_time = benchmark_conversion(
                program, "", input_file, output_file, current_benchmark, total_benchmarks)
            results.append({
                'program': program,
                'size': size,
                'conversion_time': conversion_time,
                'flags': "",
            })
            # Conversion back from hex to binary
            reconversion_time = benchmark_conversion(
                program, "-r", output_file, recon_file, current_benchmark, total_benchmarks)
            if not verify_files(input_file, recon_file):
                print_colored(f"Verification failed for {recon_file}. Exiting...", 91)  # Red text
                exit(1)
            results.append({
                'program': program,
                'size': size,
                'conversion_time': reconversion_time,
                'flags': "-r",
            })

            for flags in bench_flags:
                current_benchmark += 1
                output_file = f"{size}mb{flags}_{program}.hex"
                conversion_time = benchmark_conversion(
                    program, flags, input_file, output_file, current_benchmark, total_benchmarks)
                results.append({
                    'program': program,
                    'size': size,
                    'conversion_time': conversion_time,
                    'flags': flags,
                })
                if os.path.exists(f"{size}mb{flags}_og_xxd.hex") and os.path.exists(f"{size}mb{flags}_tinyxxd.hex"):
                    if not verify_files(f"{size}mb{flags}_og_xxd.hex", f"{size}mb{flags}_tinyxxd.hex"):
                        print_colored(
                            f"Output verification failed: these files differ: \"{size}mb{flags}_og_xxd.hex\" and \"{size}mb{flags}_tinyxxd.hex\".", 91)
                        exit(1)

            progress_bar(current_benchmark, total_benchmarks, message=f"Completed: {program} on {size}MiB")

    progress_bar(total_benchmarks, total_benchmarks, message="complete!", length=50)
    print()


def benchmark_conversion(program, flags, input_file, output_file, current, total):
    """Measures the conversion time of a program, capturing output directly, and updates the progress bar with command info."""
    cmd = f"./{program} {flags} {input_file} > {output_file}"
    command_message = f"{program} {flags} on {input_file}"
    # Update progress bar with command being run
    progress_bar(current, total, message=command_message)
    start_time = time.time()
    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    duration = time.time() - start_time
    if result.returncode != 0:
        print_colored("Command failed", 91)
        exit(1)
    return duration


def analyze_performance(results, threshold=0.05):
    """Analyzes and summarizes performance differences between og_xxd and tinyxxd for each flag and file size.

    Args:
        results (list): The list of benchmark results.
        threshold (float): The minimum relative difference to consider significant (as a fraction).

    Returns:
        list: A list of summary strings describing performance comparisons.
    """
    summaries = []

    # Group results by flags and size for comparison
    grouped = defaultdict(lambda: defaultdict(list))
    for result in results:
        grouped[(result['flags'], result['size'])][result['program']].append(result['conversion_time'])

    # Compare performances
    for (flags, size), times in grouped.items():
        if 'og_xxd' not in times or 'tinyxxd' not in times:
            continue  # Skip if either program's data is missing
        avg_og_xxd = sum(times['og_xxd']) / len(times['og_xxd'])
        avg_tinyxxd = sum(times['tinyxxd']) / len(times['tinyxxd'])
        diff = abs(avg_og_xxd - avg_tinyxxd) / max(avg_og_xxd, avg_tinyxxd)

        # Only consider differences above the threshold
        if diff > threshold:
            better_program = "og_xxd" if avg_og_xxd < avg_tinyxxd else "tinyxxd"
            percent_faster = (diff / (1 - diff)) * 100  # Calculate percentage faster relative to the slower program
            summary = f"With flags '{flags}' and size {size}MiB, {better_program} was {percent_faster:.2f}% faster."
            summaries.append(summary)

    return summaries


def summarize_performance_by_size(results, threshold=0.05):
    """Summarizes performance differences per sample size."""
    summary_data = defaultdict(lambda: defaultdict(list))
    # Collect data
    for result in results:
        summary_data[result['size']][result['program']].append(result['conversion_time'])

    # Analyze and prepare summaries
    performance_summaries_by_size = []
    for size, data in summary_data.items():
        if 'og_xxd' not in data or 'tinyxxd' not in data:
            continue  # Skip if data for either program is missing

        avg_og_xxd = sum(data['og_xxd']) / len(data['og_xxd'])
        avg_tinyxxd = sum(data['tinyxxd']) / len(data['tinyxxd'])

        if avg_og_xxd < avg_tinyxxd:
            percent_faster = ((avg_tinyxxd - avg_og_xxd) / avg_og_xxd) * 100
            if percent_faster > threshold:
                summary = f"For {size}MiB files, og_xxd was {percent_faster:.2f}% faster than tinyxxd."
                performance_summaries_by_size.append(summary)
        else:
            percent_faster = ((avg_og_xxd - avg_tinyxxd) / avg_tinyxxd) * 100
            if percent_faster > threshold:
                summary = f"For {size}MiB files, tinyxxd was {percent_faster:.2f}% faster than og_xxd."
                performance_summaries_by_size.append(summary)

    return performance_summaries_by_size


def summarize_performance_by_flag(results, threshold=0.05):
    """Summarizes performance differences per flag."""
    summary_data = defaultdict(lambda: defaultdict(list))

    # Collect data
    for result in results:
        summary_data[result['flags']][result['program']].append(result['conversion_time'])

    # Analyze and prepare summaries
    performance_summaries_by_flag = []
    for flag, data in summary_data.items():
        if 'og_xxd' not in data or 'tinyxxd' not in data:
            continue  # Skip if data for either program is missing

        avg_og_xxd = sum(data['og_xxd']) / len(data['og_xxd'])
        avg_tinyxxd = sum(data['tinyxxd']) / len(data['tinyxxd'])

        if avg_og_xxd < avg_tinyxxd:
            percent_faster = ((avg_tinyxxd - avg_og_xxd) / avg_og_xxd) * 100
            if percent_faster > threshold:
                summary = f"With flag '{flag}', og_xxd was {percent_faster:.2f}% faster than tinyxxd."
        else:
            percent_faster = ((avg_og_xxd - avg_tinyxxd) / avg_tinyxxd) * 100
            if percent_faster > threshold:
                summary = f"With flag '{flag}', tinyxxd was {percent_faster:.2f}% faster than og_xxd."
        performance_summaries_by_flag.append(summary)

    return performance_summaries_by_flag


def generate_html_report(results):
    current_datetime_iso = datetime.now().isoformat()
    html_content = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Benchmark Results</title>
        <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f8f9fa; }
        h2 { color: #17a2b8; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #dee2e6; text-align: left; padding: 8px; }
        th { background-color: #17a2b8; color: #ffffff; }
        tr:nth-child(even) { background-color: #f2f2f2; }
        hr { border: 1px solid #17a2b8; margin-top: 40px; }
        p { color: #212529; }
        </style>
    </head>
    <body>
        <h2>Benchmark Results</h2>
        <table>
            <tr>
                <th>Program</th>
                <th>Size (MiB)</th>
                <th>Conversion Time (s)</th>
                <th>Flags</th>
            </tr>
    '''
    for result in results:
        html_content += f'''
            <tr>
                <td>{result['program']}</td>
                <td>{result['size']}</td>
                <td>{result['conversion_time']:.2f}</td>
                <td>{result['flags']}</td>
            </tr>
        '''

    html_content += '''
        </table>
    </body>
    </html>
    '''
    # '''

    html_content += "<hr>"

    performance_summaries = analyze_performance(results)
    for summary in performance_summaries:
        html_content += f"<p>{summary}</p>"

    html_content += "<hr>"

    # per-size performance summary
    performance_summaries_by_size = summarize_performance_by_size(results)
    for summary in performance_summaries_by_size:
        html_content += f"<p>{summary}</p>"

    html_content += "<hr>"

    # per-flag performance summary
    performance_summaries_by_flag = summarize_performance_by_flag(results)
    for summary in performance_summaries_by_flag:
        html_content += f"<p>{summary}</p>"

    html_content += "<hr>"

    html_content += f"<p>Report generated on: {current_datetime_iso}</p>"

    html_content += "</body></html>"

    filename = "benchmark_results.html"
    with open(filename, "w") as file:
        file.write(html_content)
    # '''
    print(f"Wrote {filename}.")


def generate_markdown_report(results):
    current_datetime_iso = datetime.now().isoformat()
    md_content = "# Benchmark Results\n\n"

    # Add the table header
    md_content += "| Program | Size (MiB) | Conversion Time (s) | Flags |\n"
    md_content += "|---------|------------|----------------------|-------|\n"

    # Add the table rows with the benchmark results
    for result in results:
        md_content += f"| {result['program']} | {result['size']} | {result['conversion_time']:.2f} | {result['flags']} |\n"

    # Add performance summaries
    md_content += "\n## Performance Summaries\n"
    performance_summaries = analyze_performance(results)
    for summary in performance_summaries:
        md_content += f"- {summary}\n"

    md_content += "\n### Performance by Size\n"
    performance_summaries_by_size = summarize_performance_by_size(results)
    for summary in performance_summaries_by_size:
        md_content += f"- {summary}\n"

    md_content += "\n### Performance by Flag\n"
    performance_summaries_by_flag = summarize_performance_by_flag(results)
    for summary in performance_summaries_by_flag:
        md_content += f"- {summary}\n"

    md_content += f"\nReport generated on: {current_datetime_iso}\n"

    # Write the Markdown content to a file
    filename = "benchmark_results.md"
    with open(filename, "w") as md_file:
        md_file.write(md_content)
    print(f"Wrote {filename}.")


def cleanup_files():
    """Removes sample and output files created during the benchmark."""
    for size in sample_sizes:
        for flags in ['', '-p', '-i', '-e', '-b', '-u', '-E']:
            files_to_delete = [
                f"{size}mb.bin",
                f"{size}mb_recreated.bin",
                f"{size}mb{flags}_og_xxd.hex",
                f"{size}mb{flags}_tinyxxd.hex"
            ]
            for file in files_to_delete:
                try:
                    os.remove(file)
                except OSError as e:
                    pass


def main():
    atexit.register(cleanup_files)
    try:
        compile_programs()
        perform_benchmarks()
        generate_html_report(results)
        generate_markdown_report(results)
    except KeyboardInterrupt:
        print("\nctrl-c")


if __name__ == "__main__":
    main()
