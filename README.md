# Cafeteria-_Asincrona

## Procesamiento Asincrono

El usuario hace un request, se detecta el evento pero la respuesta no se da inmediatamente. 

Los sistemas son responsables de mandarse respuestas entre si, pasar resultados y manejar errores mientras el usuario hace otras cosas. Con esto se reducen las dependencias entre el producer y el consumer.

Ejemplos:
- Enviar formularios, la pagina no se recarga hasta enviarlo
- Subir un archivo, puede mostrar barra de progreso
- Guardar en favoritos o dar like, se actualiza el UI antes que el servidor
- Cargar contenido dinamico, skeleton loading
- Mensajes nuevos, notificaciones con sockets
- Actualizacion de datos, no siempre se muestran al instante

Ejemplo con cafeteria:
A user asks for a coffee, meanwhile another user can ask for a coffee while the other is waiting. If there is a problem with first order, the second one isn't afected. Each person receives their coffee when its done.

AWS Asincrone Services
- Message queues – Amazon SQS
    Disengage components so when one fails the other stay working. The two systems communicate from a queue, this to slow the rate of messages or petitions

    producers -> queue -> consumer
                       <- process message and delete

    SQS manages two types of queues:
    Standard: no order of messages
    FIFO: First in first out, in order

- Publish/subscribe (pub/sub) messaging – Amazon SNS
    Producer sends a message, these messages are transmited broadcast (to the rest of devices) to multiple subscribers of this topic.

    A difference with SQS is that here you don't have to make a poll to receive new messages, the notifications are send to all consumers. If multiple tools use the notifications for different actions they can act simultaneously.

    producers -> topic -> subscribers

- Data streams – Amazon Kinesis Data Streams
    Producers send a continuous secuence of notifications trough a stream or channel and consumers process from there. Similar to the queue, but can handle a large amount of messages.

    Instead of processing messages one by one streams are used to process big volumes. Many consumers can read many messages, they can see all the messages and process whats needed.

    It is usefull to process fast and big amount of data and put additions to it. In this case the consumers don't delete the mesagges.

    producers -> stream <=> consumer

<br>


## Actividad

La actividad consiste en desarrollar una aplicación en Python o TypeScript que consuma pedidos de café desde una cola de Amazon SQS y los almacene en una tabla RDS. La idea es simular el flujo de una cafetería: los pedidos se envían a SQS para evitar saturación, la app los recibe, extrae coffee_type y timestamp, los inserta en la tabla coffee_orders con order_status = 'created', y luego borra el mensaje de SQS para evitar duplicados.

Se puede iniciar con comandos de AWS CLI para crear la cola, enviar mensajes de prueba y recibir/borrar mensajes, pero la meta es automatizar todo en la app desplegada en EC2. La tabla RDS se crea con:

CREATE TABLE coffee_orders (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    coffee_type VARCHAR(50) NOT NULL,
    order_status VARCHAR(20) NOT NULL DEFAULT 'created'
);

aws cli    ----->  SQS   -----> app.py -----> RDS
sqs send

<br>


## Descripcion de Desarrollo

CLI o productor envia mensaje a la cola de SQS
"TipoCafé|YYYY-MM-DD HH:MM:SS"

La aplicacion corre en un script de python en una instancia EC2
Procesa cada mensaje: parsea el cuerpo, inserta un registro en RDS con estado 'created'.
- Si la inserción es exitosa, elimina el mensaje de la cola.
- Si ocurre un error, el mensaje no se elimina

<br>


### Componentes

- Instancia EC2 con ubuntu
- Base de datos PostgreSQL en RDS
- Queue SQS 
- Security Groups puerto 5432 y hacia internet para acceder a cola

Variables a guardar:
```
[default]
aws_access_key_id=
aws_secret_access_key=
aws_session_token=

QUEUE_URL=
DB_ENDPOINT=
SG_ID=
INSTANCE_ID=
PUBLIC_IP=
```

<br>


## Recursos

### Entorno Local

**Enter to AWS Sandbox and copy new credentials**    
```Details - Show - AWS CLI - Show```

<br>

**Configure credentials in Ubuntu bash**   
Open ubunto bash:       
```aws configure```  

Enter this data:     
```AWS Access Key ID```  
```AWS Secret Access Key```  
```AWS Session Token```  
```Default region name [us-east-1]```    
```Default output format [json]``` 

<br>

**See if AWS credentials were correctly configured**     
```cat ~/.aws/credentials```   

<br>

**Deactivate paginator less to avoid visual errors:**     
```export AWS_PAGER=cat```

<br>


### Cola

**Crear cola**   
```aws sqs create-queue --queue-name cafeteria-queue```

**Guardar url de cola**  
```QUEUE_URL=$(aws sqs get-queue-url --queue-name cafeteria-queue --query QueueUrl --output text)```

**Ver subredes disponibles**  
```aws ec2 describe-subnets --query "Subnets[*].SubnetId" --output text```

**Crear Grupo de Subredes RDS**  
```aws rds create-db-subnet-group --db-subnet-group-name cafeteria-subnet-group --subnet-ids subnet-069880b6561f283f3 subnet-05735f7ced63c4df7 --db-subnet-group-description "Subnet group for cafeteria"```

<br>


### Base de Datos

**Crear instancia RDS**  
```aws rds create-db-instance --db-instance-identifier cafeteria-db --db-instance-class db.t3.micro --engine postgres --master-username cafeteria_user --master-user-password Cafeteria1234 --allocated-storage 20 --db-subnet-group-name cafeteria-subnet-group --publicly-accessible --backup-retention-period 0 --no-multi-az --port 5432```

**Ver si instancia esta funcionando**    
```aws rds describe-db-instances --db-instance-identifier cafeteria-db --query 'DBInstances[0].DBInstanceStatus' --output text```

Esperar a que diga available 

**Obtener endpoint**     
```DB_ENDPOINT=$(aws rds describe-db-instances --db-instance-identifier cafeteria-db --query 'DBInstances[0].Endpoint.Address' --output text)```    

**Obtener id de grupo de seguridad de instancia RDS**  
```SG_ID=$(aws rds describe-db-instances --db-instance-identifier cafeteria-db --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text)```

**Abrir puerto 22**  
```aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0```

**Autorizar acceso desde cualquier ip**  
```aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5432 --cidr 0.0.0.0/0```

**Instalar PostgreSQL**  
```sudo apt update && sudo apt install postgresql-client -y ```

**Conectarse**   
```psql -h $DB_ENDPOINT -U cafeteria_user -d postgres```

**Crear Tabla**  
```CREATE TABLE coffee_orders (id SERIAL PRIMARY KEY, timestamp TIMESTAMP NOT NULL, coffee_type VARCHAR(50) NOT NULL, order_status VARCHAR(20) NOT NULL DEFAULT 'created');```

**Verificar que la tabla se creo**   
```\dt```

**Salir de psql**    
```\q```

<br>


### EC2

**Crear llaves para instancia EC2**  
```aws ec2 create-key-pair --key-name cafeteria-key --query 'KeyMaterial' --output text > cafeteria-key.pem```

**Dar permisos**     
```chmod 400 cafeteria-key.pem```

**Lanzar instancia EC2 con ubuntu**  
```INSTANCE_ID=$(aws ec2 run-instances --image-id ami-0c7217cdde317cfec --instance-type t2.micro --key-name cafeteria-key --security-group-ids $SG_ID --associate-public-ip-address --query 'Instances[0].InstanceId' --output text)```

**Obtener IP de instancia**  
```PUBLIC_IP=$(aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)```

**Ver estado de instancia**  
```aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].State.Name'```

Esperar a que diga running

**Conectarse por ssh**   
```ssh -i cafeteria-key.pem ubuntu@$PUBLIC_IP```

**Remote sesion uses color color palette of 256**    
```export TERM=xterm-256color```

<br>


### Src de Proyecto

**Terminal 2**   

**Ir a carpeta donde copiar archivos fuera de src**         
```cd "/mnt/d/<project-folder-route>"```

**Copiar archivos a la instancia EC2**   
```scp -i ~/cafeteria-key.pem -r src ubuntu@$PUBLIC_IP:/home/ubuntu```

Regresar a Terminal 1

**Verificar que archivos se subieron**   
```cd src```     
```ls```     
```cd ..```

<br>


### Entorno Remoto

**Instalar python**  
```sudo apt update && sudo apt install -y python3 python3-pip```

**Aceptar OK**   
```Tab - OK - Enter```

**Instalar dependencias**    
```pip3 install boto3 psycopg2-binary```

**Obtener AWS Credenciales**    
```Details - Show - AWS CLI - Show```

**Create folder and paste credentials**  
```mkdir -p ~/.aws```    
```vi ~/.aws/credentials ```

<br>

**Exit credentials file**    
```esc```    
```:wq```

<br>

**See if AWS credentials were correctly configured**     
```cat ~/.aws/credentials```

<br>


## Aplicacion

### Ejecutar Aplicacion

**Run server application**    
```cd src```     

**Dar permisos de ejecucion**    
```chmod +x consumer.py```

**Ejecutar aplicacion**  
```python3 consumer.py```

<br>


### Pruebas

**Mensajes de prueba**   
```aws sqs send-message --queue-url $QUEUE_URL$ --message-body "Latte|2025-02-26 10:30:00"```

```aws sqs send-message --queue-url $QUEUE_URL$ --message-body "Cappuccino|2025-02-26 10:31:00"```

```aws sqs send-message --queue-url $QUEUE_URL$ --message-body "Espresso|2025-02-26 10:32:00"```

**Conectar a base de datos**     
```psql -h cafeteria-db.cxyn6s2by9ap.us-east-1.rds.amazonaws.com -U cafeteria_user -d postgres```

**Consultar tabla**  
```SELECT * FROM coffee_orders;```

**Eliminar instancia EC2**   
```aws ec2 terminate-instances --instance-ids $INSTANCE_ID$```

**Eliminar base de datos RDS**   
```aws rds delete-db-instance --db-instance-identifier cafeteria-db --skip-final-snapshot```

**Eliminar cola SQS**    
```aws sqs delete-queue --queue-url $QUEUE_URL$```

**Eliminar par de llaves**   
```aws ec2 delete-key-pair --key-name cafeteria-key rm cafeteria-key.pem```
