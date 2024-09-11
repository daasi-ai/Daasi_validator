# Running the verifier on the cluster
The verifier is a rust server that listens on port 8080 for attestation reports from new miner-node instances.

## Dependencies:
1) Install rust
```
curl https://sh.rustup.rs -sSf | sh
```
2) Update the measurement in the [measurement.json](verifier/measurement.json) file with the one provided by Us.
```
{
    "measurement":"eebc08bfd660111e73ba84d25beecd088e2e70e20d79230cb2e34e810483eeff29264c260c7aeddee4098d1912ec5d35"
}
```

## Build
The verifier can be built using cargo:
```
cd verifier
// -r creates a release binary 
cargo build -r
```
The binary will be created in the target/release folder
```
cd target/release
./verifier
```

Alternatively you can both both build and run using ```cargo run``` directly from the root of the verifier directory.

By default, the verifier listens on port 8080.

## Working of the verifier
The verifier first verifies that the report is a genuine SNP report using AMD root certificates and then checks if the measurement in the report matches the expected value for the OS image.

Finally, if all checks pass, it stores the miner node's IP and certificate.