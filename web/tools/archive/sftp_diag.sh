echo "=== mounts ==="
docker inspect sftp-liguijiang --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'
echo "=== container home ==="
docker exec sftp-liguijiang sh -c 'ls -la /home/lgjsite; echo ---; ls -la /home/lgjsite/lsl | head'