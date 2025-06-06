# traits are like TS interfaces:
from collections import Dict
trait DatabaseIO:
    fn read(self, x: Int): ...
    fn write(self, data: Dict[String, Float64]): ...

@value
struct MongoConnector(DatabaseIO):
    fn read(self, x: Int) -> Float64:
        return x**x
