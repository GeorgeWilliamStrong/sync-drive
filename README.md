# Google Drive Synchronisation with Instill Catalog

Automatically synchronise, process, and index files within a Google Drive directly to Instill Catalog.

## Prerequisites

1. **Git**: Ensure Git is installed on your system.
2. **Conda**: Make sure you have Conda (or MiniConda) installed. You can download it from [here](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html).
3. **Credentials**: You will also need access to the `credentials.json` file to authenticate.

## Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/GeorgeWilliamStrong/sync-drive
cd sync-drive
REPO_DIR=$(pwd)
```

### 2. Setup the Environment

```bash
conda create --name drive_sync
conda activate drive_sync
conda install pip
pip install -r requirements.txt
```

### 3. Make the Script Executable

```bash
chmod +x script.py
```

### 4. Create the Synchronization Script

Create a script to automate the synchronization process and set it up as a cron job:

```bash
cd
mkdir ~/.scripts && cd ~/.scripts

cat <<EOF > sync.sh
#!/bin/bash
echo "Synchronising"

source ~/.zshrc
conda activate drive_sync

cd $REPO_DIR
python script.py

echo "Synchronisation complete"
EOF

chmod +x sync.sh
```

Note that if you are using `bashrc`, you will need to replace `.zshrc` with `.bashrc` in the above snippet.

### 5. Setup the Cron Job

Schedule the synchronization script to run at regular intervals. For example, to run the script every minute:

```bash
echo "* * * * * cd ~/.scripts && ./sync.sh >/tmp/stdout.log 2>/tmp/stderr.log" | crontab -
```
