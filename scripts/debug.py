import math
import pandas as pd

from pynvml.smi import nvidia_smi

queries = [
    'pstate',                   # current performance state
    'temperature.gpu',          # core CPU temperature in celcius
    'utilization.gpu',
    'utilization.memory',
    'memory.total',
    'memory.used',
]

nvsmi = nvidia_smi.getInstance()
status = nvsmi.DeviceQuery(','.join(queries))
info = pd.DataFrame.from_records(list(map(lambda gpu: {
    'pstate': gpu["performance_state"],
    'gpu': f'{gpu["utilization"]["gpu_util"]}%',
    'memory': f'{gpu["utilization"]["memory_util"]}%',
    'temp': f'{math.ceil(gpu["temperature"]["gpu_temp"] * 1.8) + 32}°F'
}, status['gpu'])))

print(info)