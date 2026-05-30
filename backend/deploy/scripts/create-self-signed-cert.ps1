param(
    [string]$CertDir = ".\deploy\nginx\certs",
    [string]$CommonName = "localhost",
    [string]$SubjectAltName = "DNS:localhost,IP:127.0.0.1"
)

New-Item -ItemType Directory -Force -Path $CertDir | Out-Null
$ResolvedCertDir = (Resolve-Path $CertDir).Path

docker run --rm `
    -v "${ResolvedCertDir}:/certs" `
    alpine/openssl req -x509 -nodes -newkey rsa:2048 -days 365 `
    -keyout /certs/privkey.pem `
    -out /certs/fullchain.pem `
    -subj "/CN=${CommonName}" `
    -addext "subjectAltName=${SubjectAltName}"
