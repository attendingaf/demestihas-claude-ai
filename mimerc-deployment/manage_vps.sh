#!/bin/bash

VPS_HOST="root@178.156.170.161"
VPS_DIR="/root/mimerc"

case "$1" in
    status)
        echo "Checking VPS services status..."
        ssh $VPS_HOST "cd $VPS_DIR && docker-compose ps"
        ;;
    logs)
        SERVICE=${2:-""}
        if [ -z "$SERVICE" ]; then
            ssh $VPS_HOST "cd $VPS_DIR && docker-compose logs --tail=50"
        else
            ssh $VPS_HOST "cd $VPS_DIR && docker-compose logs --tail=50 $SERVICE"
        fi
        ;;
    restart)
        SERVICE=${2:-""}
        if [ -z "$SERVICE" ]; then
            ssh $VPS_HOST "cd $VPS_DIR && docker-compose restart"
        else
            ssh $VPS_HOST "cd $VPS_DIR && docker-compose restart $SERVICE"
        fi
        ;;
    stop)
        ssh $VPS_HOST "cd $VPS_DIR && docker-compose down"
        ;;
    start)
        ssh $VPS_HOST "cd $VPS_DIR && docker-compose up -d"
        ;;
    update)
        echo "Updating deployment..."
        ./deploy_to_vps.sh
        ;;
    shell)
        SERVICE=${2:-agent}
        ssh $VPS_HOST "docker exec -it mimerc-$SERVICE /bin/sh"
        ;;
    health)
        echo "Checking health status..."
        curl -s http://178.156.170.161:8002/health | python3 -m json.tool
        ;;
    test)
        echo "Testing API..."
        curl -s -X POST http://178.156.170.161:8002/chat \
          -H "Content-Type: application/json" \
          -d '{"message":"Show my list","thread_id":"test"}' | python3 -m json.tool
        ;;
    *)
        echo "Usage: $0 {status|logs|restart|stop|start|update|shell|health|test} [service]"
        echo ""
        echo "Commands:"
        echo "  status              - Show status of all services"
        echo "  logs [service]      - Show logs (optionally for specific service)"
        echo "  restart [service]   - Restart services"
        echo "  stop                - Stop all services"
        echo "  start               - Start all services"
        echo "  update              - Redeploy from local"
        echo "  shell [service]     - Get shell access to container"
        echo "  health              - Check API health"
        echo "  test                - Test API with sample request"
        echo ""
        echo "Services: postgres, agent, telegram"
        exit 1
        ;;
esac
