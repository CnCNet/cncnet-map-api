# Load your env file to the shell
# usage:
# $ source load_env.sh
# $ read_env {optional specific env file. Defaults to ".env"}
read_env() {
  local filename="${1:-.env}"

  if [ ! -f "$filename" ]; then
    echo "missing ${filename} file"
    exit 1
  fi

  echo "reading .env file..."
  while read -r LINE; do
    if [[ $LINE != '#'* ]] && [[ $LINE == *'='* ]]; then
      export "${LINE?}"
    fi
  done < "$filename"
}
