# Security and Secret Handling

Do not commit GitHub tokens, cloud credentials, raw SCADA files, private keys, or generated credential-bearing URLs.

The repository contains research code and derived evidence. Security reports should avoid attaching raw operational data. For a token exposure, revoke the token immediately in GitHub Settings, then create a replacement with the smallest required scope.

The public research package is intended to contain source code, manifests, documentation, and derived evidence that can be redistributed. Raw data and local caches remain outside Git history unless their license and size are explicitly reviewed.
