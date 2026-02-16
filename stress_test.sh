#!/bin/bash
# stress_test.sh: Benchmarking QFA-LTL Robustness Boundary

# Ensure output directory exists
mkdir -p outputs

# Header for our results file
echo "Noise,MeasuredVal,Threshold,Verdict" > results.csv

echo "Starting Stress Test on GHZ State..."
echo "------------------------------------"

# Loop from 0.0 to 1.0 in 0.1 increments
for n in 0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0
do
    echo -n "Testing Noise Level: $n ... "
    
    # Run the verifier. 
    # Note: Ensure the PYTHONPATH is set correctly for your structure
    OUT=$(python3 verify.py --circuit examples/ghz.qasm --spec "F(p > t)" --metric parity --target "000, 111" --noise $n)
    
    # Extract values using grep and awk
    VAL=$(echo "$OUT" | grep "Measured Val" | awk '{print $NF}')
    ANC=$(echo "$OUT" | grep "Adaptive Anchor" | awk '{print $NF}')
    VER=$(echo "$OUT" | grep "VERDICT" | awk '{print $NF}')
    
    # Check if we actually got values to avoid empty rows in CSV
    if [ -z "$VAL" ]; then
        echo "[ERROR]"
    else
        echo "$n,$VAL,$ANC,$VER" >> results.csv
        echo "[$VER] (Val: $VAL / Anc: $ANC)"
    fi
done

echo "------------------------------------"
echo "Stress Test Complete."
echo "View results with: column -s, -t < results.csv"
