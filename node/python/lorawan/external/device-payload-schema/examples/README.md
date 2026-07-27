# Examples

Usage examples for the payload codec protocol buffers.

## Python Example

```python
from gen.python.payload.v1 import schema_pb2

# Create a schema message
schema = schema_pb2.Schema()
schema.name = "temperature_sensor"
schema.version = 1

print(schema)
```

## Go Example

```go
package main

import (
    "fmt"
    pb "github.com/lorawan-schema/payload-codec/gen/go/payload/v1"
)

func main() {
    schema := &pb.Schema{
        Name: "temperature_sensor",
        Version: 1,
    }
    fmt.Println(schema)
}
```

## TypeScript Example

```typescript
import { Schema } from '../gen/typescript/payload/v1/schema_pb';

const schema = new Schema();
schema.setName('temperature_sensor');
schema.setVersion(1);

console.log(schema.toObject());
```
