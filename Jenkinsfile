pipeline {
    agent{
        label 'windows'

    }
environment {

        PATH             = "C:\\WINDOWS\\SYSTEM32;C:\\WINDOWS\\System32\\WindowsPowerShell\\v1.0\\;C:\\Users\\neoan\\AppData\\Roaming\\npm;C:\\Progra~1\nodejs\\;C:\\Program Files\\Docker\\Docker\\resources\\bin;C:\\Program Files\\Git\\bin;"
        PROJECT_PATH     = "E:\\workspace\\F\\flutter\\wblester_ai"
   }
   options { 
       timestamps()
       }
      tools {

        nodejs 'node'

    }
    parameters{
		
		choice(name:"targetEnvironment", choices :  ["Production","Test"], description: "Build on local machine or push to remote repo")
        string(name:"branchName", defaultValue :"prod", description :"Git branch name")
		string(name:"commitMessage", defaultValue :"Correct Error: ", description :"Git commit message")
		choice(name:"shouldPush", choices : [ "Yes","No"],description: "Push to updates to Git:https://github.com/neoandrey/juice/")	
	}
    
    stages {

        stage('Commit changes to GitHub') {
            steps{
                dir(PROJECT_PATH )  {
                script{
                    powershell (script:""" 
                    \$currentBranch = git branch --show-current
                    if( \$currentBranch -ne "${params.branchName}"){
                        git switch "${params.branchName}"
                    }
                
                    \$commitCount = git rev-list --count HEAD
                    \$commitMessage = "[Commit #\$commitCount]: ${params.commitMessage.replace('\"','').replaceAll('\'','')}"
                    git add .
                    git commit -am \$commitMessage 
                    """, returnStdout:true)
                 }
           }


        }
        }
        
        stage('Push changes to GitHub') {
         when {
                expression {params.shouldPush == "Yes"}
            }
            steps{
                dir(PROJECT_PATH )  {
                script{
                    powershell (script:""" 
                    git push origin "${params.branchName}"
                    """, returnStdout:true)
                 }
           }


        }
        }

  stage('Run Docker Container') {
                when {
                expression {params.targetEnvironment == "Test"}
            }

           steps{
       dir(PROJECT_PATH )  {
                    powershell (script:"""
                    docker-compose -f docker-compose.remote.yml up -d ---force-recreate
                                """, returnStdout:true)
                 
           }
           }
     }

    }
}
