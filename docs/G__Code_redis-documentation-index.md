# Redis Documentation Index

**Created:** 2025-11-30  
**Purpose:** Complete Redis documentation reference for Juniper Memory System  
**Maintenance:** Quarterly review (next: 2026-02-28)  

## Quick Navigation

- [Platform Overview](#platform-overview)
- [Core Data Types](#core-data-types)
- [Redis Clients & Programming](#redis-clients--programming)
- [Clustering & Scaling](#clustering--scaling)
- [Persistence & Durability](#persistence--durability)
- [Security & Authentication](#security--authentication)
- [Performance & Memory Optimization](#performance--memory-optimization)
- [Redis Cloud & Enterprise](#redis-cloud--enterprise)
- [Administration & Operations](#administration--operations)
- [Juniper Integration Patterns](#juniper-integration-patterns)

---

## Platform Overview

### Core Redis Features
- **About Redis**: https://redis.io/docs/about/
- **Getting Started**: https://redis.io/docs/latest/get-started/
- **FAQ**: https://redis.io/docs/latest/develop/get-started/faq/
- **Data Types Overview**: https://redis.io/docs/latest/develop/data-types/

### Redis Variants
- **Redis Open Source**: Self-hosted, community version
- **Redis Cloud**: Managed service (AWS, GCP, Azure)
- **Redis Enterprise**: Commercial on-premises solution
- **Redis Stack**: Extended Redis with modules (JSON, Search, Graph, TimeSeries)

---

## Core Data Types

### Basic Data Types
- **Strings**: https://redis.io/docs/latest/develop/data-types/strings/
  - Binary-safe strings up to 512MB
  - Commands: SET, GET, MSET, MGET, INCR, APPEND
  - Use cases: Caching, counters, session storage

- **Hashes**: https://redis.io/docs/latest/develop/data-types/hashes/
  - Field-value collections (like Python dict)
  - Commands: HSET, HGET, HMGET, HGETALL, HINCRBY
  - Use cases: Object storage, user profiles
  ```bash
  HSET bike:1 model "Deimos" brand "Ergonom" price 4972
  HGET bike:1 model  # Returns: "Deimos"
  ```

- **Lists**: https://redis.io/docs/latest/develop/data-types/lists/
  - Ordered collections with duplicate values
  - Commands: LPUSH, RPUSH, LPOP, RPOP, LRANGE, LLEN
  - Use cases: Queues, activity feeds, recent items

- **Sets**: https://redis.io/docs/latest/develop/data-types/sets/
  - Unordered unique string collections
  - Commands: SADD, SREM, SISMEMBER, SINTER, SUNION, SDIFF
  - Use cases: Unique tracking, tagging, relationships
  ```bash
  SADD bikes:racing:usa bike:1 bike:4
  SINTER bikes:racing:france bikes:racing:usa  # Set intersection
  ```

- **Sorted Sets (ZSets)**: https://redis.io/docs/latest/develop/data-types/sorted-sets/
  - Unique strings ordered by score
  - Commands: ZADD, ZRANGE, ZRANK, ZREM, ZINCRBY
  - Use cases: Leaderboards, priority queues, rate limiters
  ```bash
  ZADD racer_scores 10 "Norem" 12 "Castilla" 8 "Sam-Bodden"
  ZRANGE racer_scores 0 -1  # Returns ordered by score
  ```

### Advanced Data Types
- **Streams**: https://redis.io/docs/latest/develop/data-types/streams/
  - Append-only log structure
  - Use cases: Event streaming, time-series data, messaging

- **Geospatial**: https://redis.io/docs/latest/develop/data-types/geospatial/
  - Location-based data with radius queries
  - Commands: GEOADD, GEORADIUS, GEODIST

- **HyperLogLog**: https://redis.io/docs/latest/develop/data-types/hyperloglogs/
  - Probabilistic cardinality estimation
  - Use cases: Unique visitor counting

### Extended Data Types (Redis Stack)
- **JSON**: https://redis.io/docs/latest/develop/data-types/json/
  - Native JSON document storage
  - JSONPath query support

- **Search**: Full-text search and secondary indexing
- **Graph**: Graph database capabilities
- **TimeSeries**: Time-series data management

---

## Redis Clients & Programming

### Official Client Libraries
- **Python (redis-py)**: https://redis.io/docs/latest/develop/clients/redis-py/
  ```python
  import redis
  r = redis.Redis(host='localhost', port=6379, db=0)
  r.set('key', 'value')
  r.get('key')  # Returns b'value'
  ```

- **Node.js (node-redis)**: https://redis.io/docs/latest/develop/clients/node-redis/
  ```javascript
  import { createClient } from 'redis';
  const client = createClient();
  await client.connect();
  await client.set('key', 'value');
  const value = await client.get('key');
  ```

- **Java (Jedis)**: https://redis.io/docs/latest/develop/clients/jedis/
  ```java
  import redis.clients.jedis.UnifiedJedis;
  UnifiedJedis jedis = new UnifiedJedis("redis://localhost:6379");
  jedis.set("key", "value");
  String value = jedis.get("key");
  ```

- **Java (Lettuce)**: Async/reactive Java client
- **Go (go-redis)**: https://redis.io/docs/latest/develop/clients/go-redis/
- **C# (NRedisStack)**: .NET client with Stack support

### Client Connection Patterns
```python
# Basic connection
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Connection pool (recommended for production)
pool = redis.ConnectionPool(host='localhost', port=6379, max_connections=20)
r = redis.Redis(connection_pool=pool)

# Redis Cloud connection
r = redis.Redis(
    host='redis-endpoint.cloud.redislabs.com',
    port=12345,
    password='password',
    ssl=True
)
```

### Authentication & Security
- **AUTH Command**: https://redis.io/docs/latest/commands/auth/
  ```bash
  AUTH username password
  AUTH default temp_pass
  ```

- **ACL (Access Control Lists)**: Fine-grained user permissions
- **TLS/SSL**: Encrypted connections
- **Protected Mode**: Default security for Redis 3.2+

---

## Clustering & Scaling

### Redis Cluster (Open Source)
- **Cluster Specification**: https://redis.io/docs/latest/operate/oss_and_stack/reference/cluster-spec/
- **Scaling Guide**: https://redis.io/docs/latest/operate/oss_and_stack/management/scaling/
- **Key Features**:
  - Automatic data sharding across 16,384 hash slots
  - Master-replica replication
  - Automatic failover
  - Linear scaling to 1000+ nodes

```bash
# Cluster commands
CLUSTER NODES              # View cluster topology
CLUSTER SLOTS               # View slot assignment
CLUSTER FAILOVER            # Manual failover
CLUSTER REPLICATE node-id   # Configure replica
```

### Redis Enterprise Clustering
- **Database Clustering**: https://redis.io/docs/latest/operate/rs/databases/durability-ha/clustering/
- **Features**:
  - Transparent to clients (single endpoint)
  - Cross-slot operations support
  - Custom hash policies
  - Automatic resharding

### Sharding Strategies
- **Hash Tags**: Force keys to same slot using {tag} syntax
- **Multi-key Operations**: Limited to same slot in clustered setups
- **Resharding**: Manual or automatic data redistribution

---

## Persistence & Durability

### RDB Snapshots
- **Documentation**: https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/
- **Features**:
  - Point-in-time snapshots
  - Compact binary format
  - Faster restarts with large datasets
  - Background saving with fork()

```bash
# RDB configuration
save 900 1      # Save if ≥1 key changed in 900 seconds
save 300 10     # Save if ≥10 keys changed in 300 seconds
save 60 10000   # Save if ≥10000 keys changed in 60 seconds
```

### AOF (Append Only File)
- **Features**:
  - Write operation log
  - Better durability than RDB
  - Automatic log rewriting
  - Three fsync policies

```bash
# AOF configuration
appendonly yes
appendfsync everysec    # everysec | always | no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
```

### Persistence Strategies
- **RDB Only**: Better performance, some data loss risk
- **AOF Only**: Better durability, larger files
- **RDB + AOF**: Maximum safety, higher resource usage
- **No Persistence**: Cache-only mode

### Redis Cloud Persistence
- **Options**: https://redis.io/docs/latest/operate/rc/databases/configuration/data-persistence/
  - AOF every write (Pro only)
  - AOF every second
  - Snapshots (1h, 6h, 12h intervals)
  - No persistence

---

## Performance & Memory Optimization

### Memory Optimization
- **Guide**: https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/memory-optimization/
- **Strategies**:
  - Use appropriate data types
  - Hash encoding optimization
  - Memory-efficient key naming
  - Expiration policies

```bash
# Memory optimization settings
hash-max-ziplist-entries 512
hash-max-ziplist-value 64
list-max-ziplist-size -2
set-max-intset-entries 512
zset-max-ziplist-entries 128
```

### Performance Tuning
- **Benchmarking**: https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/benchmarks/
- **Best Practices**:
  - Use connection pooling
  - Pipeline commands when possible
  - Avoid blocking operations in production
  - Monitor memory usage with INFO command

### Memory Management
```bash
# Memory information
INFO memory
MEMORY USAGE keyname      # Memory used by specific key
MEMORY STATS              # Detailed memory statistics

# Eviction policies
maxmemory 2gb
maxmemory-policy allkeys-lru  # LRU eviction when memory limit hit
```

---

## Security & Authentication

### Authentication Methods
- **Password-only**: Basic requirepass setting
- **ACL Users**: Username/password combinations with permissions
- **Certificate-based**: X.509 client certificates
- **OIDC Integration**: Enterprise feature

### ACL (Access Control Lists)
```bash
# User management
ACL SETUSER alice on >password ~cached:* +get +set
ACL LIST                   # List all users
ACL WHOAMI                 # Current user info
ACL DELUSER username       # Delete user
```

### Network Security
- **Protected Mode**: Enabled by default
- **Bind Configuration**: Limit network interfaces
- **TLS/SSL**: Encrypt client-server communication
- **Firewall Rules**: Network-level access control

---

## Redis Cloud & Enterprise

### Redis Cloud
- **Quick Start**: https://redis.io/docs/latest/operate/rc/rc-quickstart/
- **Features**:
  - Fully managed service
  - Multi-cloud deployment (AWS, GCP, Azure)
  - Auto-scaling and high availability
  - Built-in security and compliance

### Redis Enterprise
- **Active-Active**: https://redis.io/docs/latest/operate/rs/databases/active-active/
- **Features**:
  - Multi-master replication
  - Conflict-free replicated data types (CRDTs)
  - Cross-datacenter synchronization

### Deployment Options
```bash
# Redis Cloud connection
redis-cli -h redis-endpoint.cloud.redislabs.com -p 12345 -a password --tls

# Enterprise cluster connection
redis-cli -h cluster.enterprise.local -p 12000
```

---

## Administration & Operations

### Redis CLI Operations
```bash
# Basic operations
redis-cli INFO                    # Server information
redis-cli PING                    # Test connectivity
redis-cli CONFIG GET maxmemory    # Get configuration
redis-cli CONFIG SET timeout 300  # Set configuration

# Monitoring
redis-cli MONITOR                 # Real-time command monitoring
redis-cli --latency              # Latency monitoring
redis-cli --stat                 # Live statistics
```

### Monitoring & Observability
```bash
# Key metrics to monitor
INFO server          # Version, uptime, process info
INFO clients         # Connected clients, blocked clients
INFO memory          # Memory usage, fragmentation
INFO stats           # Commands processed, hit rate
INFO replication     # Master/slave status
INFO cluster         # Cluster state (if applicable)
```

### Backup & Recovery
```bash
# Manual backup
BGSAVE                           # Trigger background RDB save
LASTSAVE                         # Last successful save time

# Data export/import
redis-cli --rdb dump.rdb        # Export RDB
redis-cli --eval script.lua     # Execute Lua script
```

---

## Juniper Integration Patterns

### Caching Layer Implementation
```python
# FastAPI + Redis caching pattern
import redis.asyncio as redis
import json
from fastapi import FastAPI

app = FastAPI()
redis_client = redis.Redis.from_url("redis://localhost:6379")

@app.get("/query/{query_id}")
async def cached_query(query_id: str):
    # Check cache first
    cached_result = await redis_client.get(f"query:{query_id}")
    if cached_result:
        return json.loads(cached_result)
    
    # Compute result (expensive operation)
    result = await expensive_computation(query_id)
    
    # Cache for 1 hour
    await redis_client.setex(
        f"query:{query_id}", 
        3600, 
        json.dumps(result)
    )
    return result
```

### Session Management
```python
# Memory system session tracking
class MemorySession:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def store_context(self, conversation_id: str, context: dict):
        await self.redis.hset(
            f"conversation:{conversation_id}",
            mapping={
                "context": json.dumps(context),
                "timestamp": time.time(),
                "status": "active"
            }
        )
        # Expire after 24 hours
        await self.redis.expire(f"conversation:{conversation_id}", 86400)
    
    async def get_context(self, conversation_id: str):
        context_data = await self.redis.hgetall(f"conversation:{conversation_id}")
        if context_data:
            return json.loads(context_data["context"])
        return None
```

### Document Processing Queue
```python
# Document processing with Redis lists
class DocumentQueue:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def enqueue_document(self, doc_info: dict):
        await self.redis.lpush(
            "document_queue", 
            json.dumps(doc_info)
        )
    
    async def process_documents(self):
        while True:
            # Blocking pop with timeout
            result = await self.redis.brpop("document_queue", timeout=10)
            if result:
                queue_name, doc_data = result
                doc_info = json.loads(doc_data)
                await self.process_single_document(doc_info)
```

### Memory System Graph Cache
```python
# Neo4j query result caching
class GraphQueryCache:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    async def cache_graph_result(self, cypher_query: str, result: list, ttl: int = 300):
        cache_key = f"graph:{hashlib.md5(cypher_query.encode()).hexdigest()}"
        await self.redis.setex(
            cache_key,
            ttl,
            json.dumps({
                "query": cypher_query,
                "result": result,
                "timestamp": time.time()
            })
        )
    
    async def get_cached_result(self, cypher_query: str):
        cache_key = f"graph:{hashlib.md5(cypher_query.encode()).hexdigest()}"
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)["result"]
        return None
```

### Configuration for Juniper Stack
```python
# Production Redis configuration
REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "max_connections": 100,
    "retry_on_timeout": True,
    "socket_connect_timeout": 5,
    "socket_timeout": 5,
    "connection_class": redis.Connection,
    "charset": "utf-8",
    "decode_responses": True
}

# Memory system specific settings
MEMORY_REDIS_SETTINGS = {
    "conversation_ttl": 86400,        # 24 hours
    "query_cache_ttl": 3600,          # 1 hour
    "document_processing_timeout": 30, # 30 seconds
    "max_queue_size": 10000,
    "embedding_cache_ttl": 7200       # 2 hours
}
```

### Integration with Other Juniper Services
- **Neo4j Memory API**: Cache graph traversal results
- **MongoDB Document Store**: Cache frequent document queries
- **Voyage AI Embeddings**: Cache embedding vectors
- **FastAPI Services**: Session management and response caching
- **Google Cloud Run**: Distributed caching across instances

---

## Essential Commands Quick Reference

### Data Operations
```bash
# Strings
SET key value               GET key
MSET key1 val1 key2 val2   MGET key1 key2
INCR counter               DECR counter
APPEND key value           STRLEN key

# Hashes
HSET hash field value      HGET hash field
HMSET hash f1 v1 f2 v2     HMGET hash f1 f2
HGETALL hash               HDEL hash field
HINCRBY hash field incr    HLEN hash

# Lists
LPUSH list value           RPUSH list value
LPOP list                  RPOP list
LRANGE list 0 -1           LLEN list
LTRIM list start stop      LINDEX list index

# Sets
SADD set member            SREM set member
SMEMBERS set               SCARD set
SINTER set1 set2           SUNION set1 set2
SDIFF set1 set2            SISMEMBER set value

# Sorted Sets
ZADD zset score member     ZREM zset member
ZRANGE zset 0 -1          ZREVRANGE zset 0 -1
ZRANK zset member         ZSCORE zset member
ZINCRBY zset incr member  ZCARD zset
```

### Administration
```bash
# Server
INFO [section]             PING
CONFIG GET pattern         CONFIG SET param value
TIME                       DBSIZE
FLUSHDB                    FLUSHALL
BGSAVE                     LASTSAVE

# Keys
KEYS pattern               SCAN cursor
EXISTS key                 TYPE key
TTL key                    EXPIRE key seconds
DEL key                    RENAME old new

# Monitoring
MONITOR                    CLIENT LIST
SLOWLOG GET               LATENCY LATEST
```

---

## Links & Resources

### Official Documentation
- **Main Documentation**: https://redis.io/docs/latest/
- **Command Reference**: https://redis.io/docs/latest/commands/
- **Client Libraries**: https://redis.io/docs/latest/develop/clients/
- **Redis University**: https://university.redis.com/

### Community & Tools
- **Redis GitHub**: https://github.com/redis/redis
- **Redis CLI**: Built-in command-line interface
- **Redis Insight**: Official GUI (https://redis.io/insight/)
- **Community Clients**: https://redis.io/docs/latest/integrate/

### Juniper-Specific Resources
- **Juniper Roadmap**: G:\Code\JUNIPER_ROADMAP_V1.md
- **Memory API v2.0**: [To be deployed on Cloud Run]
- **Redis Configuration**: In memory-api config files
- **Integration Examples**: This document's Juniper sections

---

**Last Updated**: 2025-11-30  
**Next Review**: 2026-02-28  
**Maintainer**: Sean Rawlings, AIM Innovations  
**Version**: 1.0
