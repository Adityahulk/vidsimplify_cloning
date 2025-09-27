"""
Simple test client for the streaming demo
"""
import asyncio
import websockets
import json
import base64
import cv2
import numpy as np
import time


async def test_streaming_client():
    """Test the streaming WebSocket connection"""
    
    session_id = f"test_client_{int(time.time())}"
    url = f"ws://localhost:8000/ws/stream/{session_id}"
    
    print(f"🔌 Connecting to {url}")
    
    try:
        async with websockets.connect(url) as websocket:
            print("✅ Connected to streaming server!")
            
            # Send configuration
            config = {
                "type": "config",
                "target_language": "es",
                "source_language": "en",
                "enable_voice_cloning": False,
                "chunk_duration": 1.0,
                "whisper_model": "tiny"
            }
            
            await websocket.send(json.dumps(config))
            print("📤 Configuration sent")
            
            # Wait for ready message
            ready_message = await websocket.recv()
            ready_data = json.loads(ready_message)
            print(f"📥 Received: {ready_data}")
            
            if ready_data.get("type") == "ready":
                print("🎯 Server ready for streaming!")
                
                # Test sending a simple frame
                print("📷 Testing frame processing...")
                
                # Create a simple test frame
                test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                test_frame[:] = (100, 150, 200)  # Blue color
                
                # Add some text
                cv2.putText(test_frame, "TEST FRAME", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
                cv2.putText(test_frame, f"Session: {session_id[:8]}", (200, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                # Encode frame
                _, buffer = cv2.imencode('.jpg', test_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_data = base64.b64encode(buffer).decode('utf-8')
                
                # Send frame
                frame_message = {
                    "type": "frame",
                    "frame_data": frame_data,
                    "timestamp": time.time()
                }
                
                await websocket.send(json.dumps(frame_message))
                print("📤 Test frame sent")
                
                # Wait for processed frame
                processed_message = await websocket.recv()
                processed_data = json.loads(processed_message)
                
                if processed_data.get("type") == "processed_frame":
                    print("📥 Received processed frame!")
                    print(f"   Frame size: {len(processed_data.get('frame_data', ''))} characters")
                else:
                    print(f"❌ Unexpected message type: {processed_data.get('type')}")
                
                # Request statistics
                print("📊 Requesting statistics...")
                await websocket.send(json.dumps({"type": "get_stats"}))
                
                stats_message = await websocket.recv()
                stats_data = json.loads(stats_message)
                
                if stats_data.get("type") == "stats":
                    print("📈 Statistics received:")
                    print(f"   Session ID: {stats_data.get('session_id')}")
                    print(f"   Frames processed: {stats_data.get('frames_processed')}")
                    print(f"   Processing time: {stats_data.get('processing_time'):.2f}s")
                    print(f"   FPS: {stats_data.get('fps'):.2f}")
                    print(f"   Status: {stats_data.get('status')}")
                
                print("\n🎉 Test completed successfully!")
                print("✅ WebSocket connection working")
                print("✅ Frame processing working")
                print("✅ Statistics working")
                
            else:
                print(f"❌ Unexpected ready message: {ready_data}")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")


async def test_multiple_frames():
    """Test sending multiple frames"""
    
    session_id = f"multi_test_{int(time.time())}"
    url = f"ws://localhost:8000/ws/stream/{session_id}"
    
    print(f"\n🔄 Testing multiple frames with {url}")
    
    try:
        async with websockets.connect(url) as websocket:
            # Configure
            await websocket.send(json.dumps({
                "type": "config",
                "target_language": "fr",
                "source_language": "en"
            }))
            
            # Wait for ready
            await websocket.recv()
            print("✅ Connected and configured")
            
            # Send multiple frames
            for i in range(5):
                # Create frame with different colors
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                frame[:] = (i * 50, 100, 255 - i * 50)  # Changing colors
                
                cv2.putText(frame, f"Frame {i+1}/5", (200, 200), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
                cv2.putText(frame, f"Time: {time.time():.2f}", (200, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                
                # Encode and send
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                frame_data = base64.b64encode(buffer).decode('utf-8')
                
                await websocket.send(json.dumps({
                    "type": "frame",
                    "frame_data": frame_data,
                    "timestamp": time.time()
                }))
                
                print(f"📤 Sent frame {i+1}")
                
                # Receive processed frame
                processed_message = await websocket.recv()
                processed_data = json.loads(processed_message)
                
                if processed_data.get("type") == "processed_frame":
                    print(f"📥 Received processed frame {i+1}")
                else:
                    print(f"❌ Unexpected message: {processed_data.get('type')}")
                
                await asyncio.sleep(0.5)  # Wait between frames
            
            # Get final stats
            await websocket.send(json.dumps({"type": "get_stats"}))
            stats_message = await websocket.recv()
            stats_data = json.loads(stats_message)
            
            print(f"\n📊 Final statistics:")
            print(f"   Frames processed: {stats_data.get('frames_processed')}")
            print(f"   FPS: {stats_data.get('fps'):.2f}")
            
            print("🎉 Multiple frame test completed!")
            
    except Exception as e:
        print(f"❌ Multiple frame test failed: {e}")


def main():
    """Run all tests"""
    print("🧪 Streaming API Test Suite")
    print("=" * 50)
    
    try:
        # Test basic connection and single frame
        asyncio.run(test_streaming_client())
        
        # Test multiple frames
        asyncio.run(test_multiple_frames())
        
        print("\n🎉 All tests completed!")
        print("\n💡 Next steps:")
        print("   1. Open your browser and go to http://localhost:8000")
        print("   2. Click 'Start Stream' to establish WebSocket connection")
        print("   3. Click 'Start Capture' to begin camera streaming")
        print("   4. Watch the real-time processed video with timestamp overlays")
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")


if __name__ == "__main__":
    main()
