# gitstat for Python 3

`gitstat.py` is a command-line tool for analyzing git repositories, exporting statistics, and generating reports. It supports a variety of options for fetching, analyzing, and outputting repository data.

This tool is inspired by [https://github.com/hoxu/gitstats](https://github.com/hoxu/gitstats) and its Python 3 adaptation from [https://github.com/KaivnD/gitstats](https://github.com/KaivnD/gitstats), with additional functionality and improvements.

## GitHub API Authentication

To use features that access the GitHub API (such as updating repository information or fetching contributors), you must set the `GITHUB_TOKEN` environment variable to your personal GitHub API token. This token should have appropriate permissions for public repository access.

**Example:**

```bash
export GITHUB_TOKEN="Bearer <your_github_token>"
```

Replace `<your_github_token>` with your actual token. This step is required before running any command that interacts with GitHub.

## Usage

### Example: Download, Analyze, and Cache a GitHub Repository

To download a git repository, fetch information about it using the GitHub API, process all the information, and cache the results, use a command like:

```bash
python3 gitstat.py -u --update-all -g https://github.com/example/repo
```

This command will:
- Download the specified git repository.
- Retrieve metadata and contributor information from the GitHub API.
- Process all available information.
- Cache the results locally for faster future access.

You can also specify which parts to update:

```bash
python3 gitstat.py -u --update-git -g https://github.com/example/repo  # Update only git information
python3 gitstat.py -u --update-github -g https://github.com/example/repo  # Update only GitHub information
```

### Example: View Results of a Previously Obtained Repository

To see the results of a previously downloaded and processed repository (using cached data), run:

```bash
python3 gitstat.py -g https://github.com/example/repo  -o console
```

This will output the analysis results to the console, using the cached data if available.

### Basic Command

```bash
python gitstat.py [options]
```

## Understanding Update and Analysis Options

Gitstats provides several options that serve different purposes:

### Key Analysis Options

| Option | Stage | Purpose | Example |
|--------|-------|---------|----------|
| `-u, --update` | Data Collection | Enables update mode to fetch and cache data | `-u` downloads all GitHub information and fetches repos |
| `-m, --months-to-analyze N` | Data Analysis | Filters the analysis to last N months | `-m 6` analyzes last 6 months of data |
| `-o, --months-offset N` | Data Analysis | Starts analysis N months back from current date | `-o 3` starts analysis from 3 months ago |
| `-a, --analyze-performance N` | Data Analysis | Analyzes author performance over N months | `-a 12` shows monthly performance for last 12 months |

**Key Differences:**
1. **When they're used**:
   - `-u` is used for update mode (when fetching from GitHub/cloning)
   - `-m`, `-o`, and `-a` are used during data analysis (when generating reports)

2. **Effect on operation**:
   - `-u` enables update mode to download and store data in cache
   - `-m` filters the already collected/cached data for statistics calculation
   - `-o` shifts the analysis window back by the specified number of months
   - `-a` generates performance analysis charts showing author metrics over time

3. **Use cases**:
   - Use `-u` when you want to download and update repository data
   - Use `-m` when you want to analyze different time windows from the same cached data
   - Use `-o` when you want to analyze a specific historical period
   - Use `-a` when you want to visualize author performance trends over time

**Examples:**

1. Update cache with all data, then analyze last 3 months:
   ```bash
   # First, update the cache with all data
   gitstat.py -u -g https://github.com/example/repo
   
   # Then analyze last 3 months
   gitstat.py -m 3 -g https://github.com/example/repo --output console
   ```

2. Use existing cache but only analyze last 6 months:
   ```bash
   gitstat.py -m 6 -g https://github.com/example/repo --output console
   ```

3. Analyze a specific historical period (6 months starting from 12 months ago):
   ```bash
   gitstat.py -m 6 -o 12 -g https://github.com/example/repo --output console
   ```

4. Generate performance analysis charts for the last 12 months:
   ```bash
   gitstat.py -a 12 -g https://github.com/example/repo --output console
   ```

5. Combine multiple options for advanced analysis:
   ```bash
   # Analyze 6 months of data starting from 3 months ago with performance charts
   gitstat.py -m 6 -o 3 -a 6 -g https://github.com/example/repo --output console
   ```

### Options

#### Generic options
- `-v`, `--verbose`            Enable verbose mode (use `-vv` for max verbosity)
- `-l`, `--logfile`            Log filename

#### Fetch options
- `--cache-folder`             Cache folder (default: `_cache`)
- `--repos-folder`             Repos folder (default: `_repos`)
- `--update-all`               Update all cache
- `--update-git`               Update cache with git-based info only
- `--git-download-only`        Clone repos only
- `--skip-existing`            Skip collecting from GitHub if exists in the cache
- `--update-github`            Update cache with GitHub-based info only
- `--update-github-anon-only`  Update cache with GitHub-based info about anonymous users only

#### Analyzer options
- `-u`, `--update`             Run in update mode - downloads all GitHub information and fetches repos

#### Stats options
- `-m`, `--months-to-analyze`  Number of last months to analyze for stats calculation (default: 12)
- `-o`, `--months-offset`     How many months back to start the analysis (e.g., 12 means start from a year ago) (default: 0)
- `-a`, `--analyze-performance` Analyze author performance over time for the specified number of months, showing monthly metrics and charts

#### Input options
- `-g`, `--github-url`         Git repo URL to analyze
- `-e`, `--excel-file`         Excel file to update
- `-f`, `--text-file`          Text file to update

#### Output options
- `-o`, `--output`             Output options: `excel`, `console`, etc.

### Example Commands

Analyze an Excel file and output results to Excel format:
```bash
python3 gitstat.py -e oss_projects.xlsx -o excel
```

Update anonymous users info from a GitHub repo:
```bash
python3 gitstat.py -u --skip-existing --update-github-anon-only -g https://github.com/example/repo
```

Update using only git-based info for a specific repo:
```bash
python3 gitstat.py -u --update-git -g https://github.com/example/repo
```

Analyze a repo for a specific number of months and output to console:
```bash
python3 gitstat.py -g https://github.com/example/repo -m 6 -o console
```

Enable verbose logging and save logs to a file:
```bash
python3 gitstat.py -g https://github.com/example/repo -v -l gitstats.log
```

#### Notes
- You can combine options as needed for your workflow.
- For best results, use a Python virtual environment (see below for setup instructions).

## Running with a Python Virtual Environment

It is recommended to use a Python virtual environment to manage dependencies and avoid conflicts. Here are the steps:

```bash
# Create a virtual environment (e.g., in .venv directory)
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On Linux/macOS
# .venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt

# Run the tool
python gitstat.py [options]
```

To deactivate the virtual environment when done, simply run:
```bash
deactivate
```
