eval "$(/opt/homebrew/bin/brew shellenv)"
export GEM_HOME=~/.gem
export PATH="/usr/bin:/usr/sbin:/bin:/sbin:/usr/local/bin:$PATH"


export JAVA_HOME=/Applications/Unity/Hub/Editor/6000.0.59f2/PlaybackEngines/AndroidPlayer/OpenJDK/
export PATH=$JAVA_HOME/bin:$PATH:.
export CLASSPATH=$JAVA_HOME/lib/tools.jar:$JAVA_HOME/lib/dt.jar:.


# Android Sdk
# export ANDROID_SDK_ROOT=/Applications/Unity/Hub/Editor/2023.1.22f1/PlaybackEngines/AndroidPlayer/SDK
export ANDROID_SDK_ROOT=/Applications/Unity/Hub/Editor/6000.0.59f2/PlaybackEngines/AndroidPlayer/SDK
export PATH=${PATH}:${ANDROID_SDK_ROOT}/tools
export PATH=${PATH}:${ANDROID_SDK_ROOT}/platform-tools
export PATH=${PATH}:${ANDROID_SDK_ROOT}/tools/bin
export PATH=${PATH}:${ANDROID_SDK_ROOT}/emulator
export ANDROID_SDK=${ANDROID_SDK_ROOT}
export ANDROID_NDK=${ANDROID_SDK_ROOT}/ndk-bundle
